#!/root/venv/odoo/bin/python
from gevent import monkey; monkey.patch_all()
import gevent
import logging
from Asterisk.Manager import Manager
from flask import Flask, jsonify
from gevent.wsgi import WSGIServer

logger = logging.getLogger('broker.py')
app = Flask(__name__)
http_server = WSGIServer(('localhost', 5000), app)
pbx = Manager(('localhost', 5038), 'user', '12341234')

@app.route('/reload')
def asterisk_reload():
  logger.info('running AMI command reload')
  result = pbx.Command('reload')
  return jsonify(result)

if __name__ == '__main__':
  logger.info('Broker started')
  flask_instance = gevent.spawn(http_server.serve_forever)
  gevent.joinall([flask_instance])
