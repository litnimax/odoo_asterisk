import tornado.web
from tornado.ioloop import IOLoop
from terminado import TermSocket, SingleTermManager

PORT = 8010
ASTERISK = '/usr/sbin/asterisk'

class MyTermSocket(TermSocket):

    def check_origin(self, origin):
        return True

if __name__ == '__main__':
    term_manager = SingleTermManager(shell_command=[ASTERISK, '-cr'])
    handlers = [
                (r"/websocket", MyTermSocket, {'term_manager': term_manager}),
               ]
    app = tornado.web.Application(handlers)
    app.listen(PORT)
    IOLoop.current().start()
