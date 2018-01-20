import logging
import os
import ssl
import tornado.web
from tornado.ioloop import IOLoop
from terminado import TermSocket, SingleTermManager
from tornado.httpserver import HTTPServer

logging.basicConfig(level=logging.DEBUG)
_logger = logging.getLogger(__name__)

ASTERISK = '/usr/bin/asterisk'

from conf import *

class MyTermSocket(TermSocket):

    def check_origin(self, origin):
        return True


class RecordingDeleteHandler(tornado.web.RequestHandler):
    def get(self):
        # Take only the right part of the path to get rid if ../../etc/password
        base_name = os.path.basename(self.get_argument('filename'))
        # Now format a clean path
        file_path = os.path.join(ASTERISK_RECORDING_FOLDER,
            base_name)
        if os.path.exists(file_path):
            _logger.info('Deleteing {}.'.format(file_path))
            os.unlink(file_path)
            self.write('DELETED')
        else:
            _logger.warning('File {} does not exist.'.format(file_path))
            self.write('NOT_FOUND')


if __name__ == '__main__':
    term_manager = SingleTermManager(shell_command=[ASTERISK, ASTERISK_ARGS])
    handlers = [
                (r'/websocket', MyTermSocket, {'term_manager': term_manager}),
                (r'/delete_recording', RecordingDeleteHandler)
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
