import gevent
from gevent.monkey import  patch_all; patch_all()
from gevent.queue import Queue
import logging
import Asterisk
from Asterisk.Manager import Manager
import xmlrpclib


logging.basicConfig()
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

conf = {}
conf['pbx_host'] = '192.168.56.51'
conf['pbx_port'] = 5038
conf['pbx_user'] = 'test'
conf['pbx_password'] = 'test'

ODOO_URL = 'http://localhost:8069'
ODOO_DB = 'odoo9_gtd'
ODOO_USER = 'admin'
ODOO_PASSWORD = 'admin'
SLEEP = 1 # Delay 10 sec before updating cdr

try:
    from local_settings import *
except ImportError:
    pass

eventQ = Queue(maxsize=10000)


def get_odoo_rpc_uid():
    try:
        common = xmlrpclib.ServerProxy('%s/xmlrpc/2/common' % ODOO_URL)
        uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASSWORD, {})
        return uid
    except Exception as e:
        logger.exception('Could not authenticate witu Odoo XML-RPC!')
        return 0

ODOO_UID = get_odoo_rpc_uid()

def odoo_rpc(model, method, arg_list, arg_dict=None):
    try:
        models = xmlrpclib.ServerProxy('%s/xmlrpc/2/object' % ODOO_URL)
        if arg_dict:
            res = models.execute_kw(ODOO_DB, ODOO_UID, ODOO_PASSWORD,
                                model, method, arg_list, arg_dict)
        else:
            res = models.execute_kw(ODOO_DB, ODOO_UID, ODOO_PASSWORD,
                                model, method, arg_list)
        return res
    except Exception as e:
        logger.exception('Could not execute %s on %s! Args: %s, *kwargs: %s' %
                                        (method, model, arg_list, arg_dict))


class QosEvents(object):

    def new_event(self, pbx, event):
        print event, event.get('Uniqueid')
        if event.get('Variable') == 'RTPAUDIOQOS':
            value = event.get('Value')
            pairs = [k for k in value.split(';') if k]
            values = {}
            for pairs in pairs:
                k,v = pairs.split('=')
                values.update({k: v})
            values.update({
                'uniqueid': event.get('Uniqueid'),
                'linkedid': event.get('Linkedid')
            })
            gevent.spawn(handle_message, values)


    def __init__(self):
        self.events = Asterisk.Util.EventCollection()
        self.events.subscribe('VarSet', self.new_event)


    def register(self, pbx):
        pbx.events += self.events


    def unregister(self, pbx):
        pbx.events -= self.events



def handle_message(message):
    # We have to give CDR some time to get into the database.
    # Actually we do not hurry at all. We just make a delay
    gevent.sleep(SLEEP)
    logger.debug(message)
    odoo_rpc('asterisk.cdr', 'log_qos', [message], {})



pbx = Manager((conf['pbx_host'], conf['pbx_port']),
              conf['pbx_user'], conf['pbx_password'])


qos_events = QosEvents()
qos_events.register(pbx)
h1 = gevent.spawn(pbx.serve_forever)
gevent.joinall([h1])

