"""Provides a request server to be used with the multiprocess handler."""

from praw.handlers import RateLimitHandler
from requests import Session
from six.moves import cPickle, socketserver
from threading import Lock


class ThreadingTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    # pylint: disable-msg=R0903,W0232

    """A TCP server that creates new threads per connection."""

    allow_reuse_address = True


class RequestHandler(socketserver.StreamRequestHandler):
    # pylint: disable-msg=W0232

    """A class that handles incoming requests.

    Requests to the same domain are cached and rate-limited.

    TODO: Cache requests (with necessary locking)

    """

    http = Session()
    last_call = {}  # Stores a two-item list: [lock, previous_call_time]
    lock = Lock()  # lock used for adding items to last_call

    def handle(self):
        """Parse the RPC, make the call, and pickle up the return value."""
        data = cPickle.load(self.rfile)  # pylint: disable-msg=E1101
        method = data.pop('method')
        if method == 'request':
            retval = self.do_request(**data)
        else:
            retval = Exception('Invalid method')
        cPickle.dump(retval, self.wfile,  # pylint: disable-msg=E1101
                     cPickle.HIGHEST_PROTOCOL)

    @RateLimitHandler.rate_limit
    def do_request(self, request, proxies, timeout, **_):
        """Dispatch the actual request and return the result."""
        print('{0} {1}'.format(request.method, request.url))
        response = self.http.send(request, proxies=proxies, timeout=timeout)
        response.raw = None  # Make pickleable
        return response


def run():
    """The entry point from the praw-multiprocess utility."""
    host = 'localhost'
    port = 10101
    server = ThreadingTCPServer((host, port), RequestHandler)
    print('Listening on {0} port {1}'.format(host, port))
    server.serve_forever()  # pylint: disable-msg=E1101