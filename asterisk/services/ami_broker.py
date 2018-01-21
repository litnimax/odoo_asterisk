# Patch all before importing other modules!
import gevent
from gevent.monkey import  patch_all; patch_all()
from gevent.queue import Queue
from gevent.pool import Event
import logging
import os
import setproctitle
import asterisk.manager
import odoorpc
from odoo_broker import OdooBroker


logging.basicConfig(level=logging.DEBUG)


class AmiBroker(OdooBroker):
    ami_disconnected = Event()
    ami_connected = Event()
    stopped = Event()
    ami_manager = None
    settings = {}
    greenlets = []

    def __init__(self):
        OdooBroker.__init__(self)
        setproctitle.setproctitle('ami_broker')
        self.ami_disconnected.set()
        self.settings['AsteriskHost']  = os.environ.get(
            'MANAGER_IP', '127.0.0.1')
        self.settings['AmiPort']  = os.environ.get(
            'MANAGER_PORT', '5038')
        self.settings['AsteriskLogin']  = os.environ.get(
            'MANAGER_LOGIN', 'odoo')
        self.settings['AsteriskPassword']  = os.environ.get(
            'MANAGER_PASSWORD', 'odoo')
        self.settings['AmiHeartbeatInterval']  = os.environ.get(
            'MANAGER_HEARTBEAT_INTERVAL', '10')
        self.spawn(self.ami_connection_loop)
        self.spawn(self.ami_heartbeat)


    def spawn(self, func, *args, **kwargs):
        try:
            self.greenlets.append(gevent.spawn(func, *args, **kwargs))
        except Exception as e:
            logging.exception(repr(e))


    def start(self):
        gevent.joinall(self.greenlets)


    def stop(self):
        self.stopped.set()
        OdooBroker.stop(self)
        ZActor.stop(self)


    def handle_asterisk_event(self, event, manager):
        # General method to spawn event handlres.
        event_handler = getattr(self, 'on_asterisk_{}'.format(event.name), None)
        if event_handler:
            gevent.spawn(event_handler, event, manager)
        else:
            logging.error('Event {} handler not found!'.format(event.name))


    def ami_connection_loop(self):
        while True:
            if self.stopped.is_set():
                return
            self.ami_manager = None
            try:
                # Create PBX connection
                manager = manager = asterisk.manager.Manager()
                logging.debug('Connecting to {}:{} with {}:{}'.format(
                    self.settings.get('AsteriskHost'),
                    self.settings.get('AmiPort'),
                    self.settings.get('AsteriskLogin'),
                    self.settings.get('AsteriskPassword'),
                ))
                manager.connect(
                    str(self.settings.get('AsteriskHost')),
                    port = int(self.settings.get('AmiPort'))
                )
                manager.login(
                    self.settings.get('AsteriskLogin'),
                    self.settings.get('AsteriskPassword')
                )
                logging.info('Managed connected.')
                manager.register_event('PeerStatus', self.handle_asterisk_event)
                manager.register_event('UserEvent', self.handle_asterisk_event)
                manager.register_event('VarSet', self.handle_asterisk_event)
                self.ami_manager = manager
                self.ami_disconnected.clear()
                self.ami_connected.set()
                self.ami_disconnected.wait()

            except asterisk.manager.ManagerSocketException as e:
                logging.error("Error connecting to the manager: %s" % e)
            except asterisk.manager.ManagerAuthException as e:
                logging.error("Error logging in to the manager: %s" % e)
            except asterisk.manager.ManagerException as e:
                logging.error("Error: %s" % e)

            logging.info('Reconnecting AMI.')
            gevent.sleep(self.settings.get('AmiReconnectTimeout'))


    def ami_heartbeat(self):
        if not self.settings.get('AmiHeartbeatInterval'):
            logging.info('AMI Heartbeat disabled.')
            return
        else:
            logging.info('Starting AMI heartbeat.')
        while True:
            try:
                self.ami_connected.wait()
                logging.debug('AMI heartbeat ping.')
                res = self.ami_manager.ping()
                if res.headers.get('Response') != 'Success':
                    raise Exception('Ping response failed!')
                gevent.sleep(int(self.settings.get('AmiHeartbeatInterval')))

            except asterisk.manager.ManagerException as e:
                self.ami_connected.clear()
                self.ami_disconnected.set()
                logging.warning('AMI ping failed, reconnect!')
                logging.debug('{}: {}'.format(e, traceback.format_exc()))

            except Exception as e:
                self.ami_connected.clear()
                self.ami_disconnected.set()
                if 'Ping response failed' in repr(e):
                    logging.warning('AMI ping failed, reconnect!')
                else:
                    logging.exception(e)


    def on_asterisk_VarSet(self, event, manager):
     # QoS of CDR
        if event.headers.get('Variable') == 'RTPAUDIOQOS':
            value = event.headers.get('Value')
            pairs = [k for k in value.split(';') if k]
            values = {}
            for pairs in pairs:
                k,v = pairs.split('=')
                values.update({k: v})
            values.update({
                'uniqueid': event.headers.get('Uniqueid'),
                'linkedid': event.headers.get('Linkedid')
            })
            gevent.sleep(self.settings.get('CdrUpdateDelay'))
            logger.debug('QoS update: \n{}'.format(json.dumps(
                values, indent=4)))
            self.odoo.env['asterisk.cdr'].log_qos(values)
        else:
            logging.debug('VarSet for {} not defined.'.format(
                event.headers.get('Variable')))


    def on_asterisk_PeerStatus(self, event, manager):
        logging.debug(dir(event))
        logging.debug(event.headers)
        if event.headers.get('ChannelType') == 'SIP':
            # We only care about SIP registrations
            return self.odoo.env['asterisk.sip_peer_status'].update_status(event.headers)



    def on_asterisk_UserEvent(self, event, manager):
        if event.headers.get('UserEvent') == 'Test':
            logging.info('Test user event')



if __name__ == '__main__':
    broker = AmiBroker()
    broker.start()
