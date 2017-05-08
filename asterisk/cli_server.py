import tornado.web
from tornado.ioloop import IOLoop
from terminado import TermSocket, SingleTermManager

PORT = 8010
ASTERISK = '/usr/local/bin/asterisk -r'

class MyTermSocket(TermSocket):
    """
    def get(self, *args, **kwargs):
        if not self.get_current_user():
            raise web.HTTPError(403)
        return super(TermSocket, self).get(*args, **kwargs)
    """
    def check_origin(self, origin):
        return True

if __name__ == '__main__':
    term_manager = SingleTermManager(shell_command=[ASTERISK])
    handlers = [
                (r"/websocket", MyTermSocket, {'term_manager': term_manager}),
                #(r"/()", tornado.web.StaticFileHandler, {'path':'index.html'}),
                #(r"/(.*)", tornado.web.StaticFileHandler, {'path':'.'}),
               ]
    app = tornado.web.Application(handlers)
    app.listen(PORT)
    IOLoop.current().start()
