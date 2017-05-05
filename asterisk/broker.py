#!/root/venv/odoo/bin/python
#from gevent import monkey; monkey.patch_all()
import gevent
from Asterisk.Manager import Manager
from flask import Flask, jsonify
from gevent.wsgi import WSGIServer

app = Flask(__name__)
http_server = WSGIServer(('localhost', 5000), app)
pbx = Manager(('localhost', 5038), 'user', '12341234')

@app.route('/reload')
def asterisk_reload():
  result = pbx.Command('reload')
  return jsonify(result)

if __name__ == "__main__":
  flask_instance = gevent.spawn(http_server.serve_forever)
  #pbx_instance = gevent.spawn(pbx.serve_forever)
  gevent.joinall([flask_instance])
 
