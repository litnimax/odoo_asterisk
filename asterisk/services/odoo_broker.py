import gevent
from gevent.monkey import  patch_all; patch_all()
from gevent.pool import Event
import json
import logging
import os
import requests
import traceback
import urllib2
import urlparse
import odoorpc

logging.basicConfig(level=logging.DEBUG)

class OdooBroker(object):
    odoo = None
    odoo_disconnected = Event()
    odoo_connected = Event()
    greenlets = []

    settings = {}

    def __init__(self):
        logging.debug('OdooBroker init.')
        self.odoo_disconnected.set()
        self.settings['OdooHost'] = os.environ.get('ODOO_IP', 'odoo')
        self.settings['OdooPort'] = os.environ.get('ODOO_PORT', '8069')
        self.settings['OdooDb'] = os.environ.get('ODOO_DB', 'asterisk')
        self.settings['OdooUser'] = os.environ.get('ODOO_USER', 'admin')
        self.settings['OdooPassword'] = os.environ.get('ODOO_PASSWORD', 'admin')
        self.settings['OdooReconnectTimeout'] = int(os.environ.get('ODOO_RECONNECT_TIMEOUT', '5'))
        self.greenlets.append(gevent.spawn(self.connect_odoo_loop))

    def stop(self):
        logging.debug('Logout from Odoo.')
        self.odoo.logout()


    def connect_odoo_loop(self):
        while True:
            try:
                host = self.settings.get('OdooHost')
                port = self.settings.get('OdooPort')
                logging.info('Connecting to Odoo at {}:{}'.format(host, port))
                odoo = odoorpc.ODOO(host, port=port)
                odoo.login(
                    self.settings.get('OdooDb'),
                    self.settings.get('OdooUser'),
                    self.settings.get('OdooPassword'),
                )
                logging.info('Connected to Odoo.')
                self.odoo = odoo
                self.odoo_disconnected.clear()
                self.odoo_connected.set()
                self.odoo_disconnected.wait() # Wait forever for disconnect

            except Exception as e:
                if 'Connection refused' in repr(e):
            	       logging.error('Odoo refusing connection.')
                else:
                    logging.exception(e)

                gevent.sleep(self.settings.get('OdooReconnectTimeout'))
