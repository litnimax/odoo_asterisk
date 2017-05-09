import logging
import ssl
import tornado.web
from tornado.ioloop import IOLoop
from terminado import TermSocket, SingleTermManager
from tornado.httpserver import HTTPServer

logging.basicConfig()
_logger = logging.getLogger(__name__)


PORT = 8010
ASTERISK = '/usr/sbin/asterisk'
ASTERISK_ARGS = '-cr'

SSL_ENABLED = False
SSL_CERT = './cert.pem'
SSL_KEY = './privkey.pem'

try:
    from local_conf import *
except ImportError:
    _logger.warning('No local_conf.py found or import error!')


class MyTermSocket(TermSocket):

    def check_origin(self, origin):
        return True

if __name__ == '__main__':
    term_manager = SingleTermManager(shell_command=[ASTERISK, ASTERISK_ARGS])
    handlers = [
                (r"/websocket", MyTermSocket, {'term_manager': term_manager}),
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
server.listen(PORT)
IOLoop.current().start()
