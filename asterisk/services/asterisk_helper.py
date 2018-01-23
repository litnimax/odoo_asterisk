import logging
import os
import ssl
import tornado.web
from tornado.ioloop import IOLoop
from terminado import TermSocket, SingleTermManager
from tornado.httpserver import HTTPServer

logging.basicConfig(level=logging.DEBUG)
_logger = logging.getLogger(__name__)

ASTERISK = os.environ.get('ASTERISK_BINARY', '/usr/sbin/asterisk')
ASTERISK_ARGS = '-cr'
SSL_ENABLED = False
LISTEN_ADDRESS = os.environ.get('CONSOLE_LISTEN_ADDRESS', '0.0.0.0')
LISTEN_PORT = int(os.environ.get('CONSOLE_LISTEN_PORT', '8010'))


class MyTermSocket(TermSocket):

    def check_origin(self, origin):
        return True


if __name__ == '__main__':
    term_manager = SingleTermManager(shell_command=[ASTERISK, ASTERISK_ARGS])
    handlers = [
                (r'/websocket', MyTermSocket, {'term_manager': term_manager}),
               ]

# Create SSL context
if SSL_ENABLED:
    ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_ctx.load_cert_chain(SSL_CERT, SSL_KEY)
else:
    ssl_ctx = None

# Start server
app = tornado.web.Application(handlers)
server = HTTPServer(app, ssl_options=ssl_ctx)
server.listen(LISTEN_PORT, address=LISTEN_ADDRESS)
IOLoop.current().start()
