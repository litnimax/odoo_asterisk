# Patch all before importing other modules!
import gevent
from gevent.monkey import  patch_all; patch_all()
from gevent.queue import Queue
from Queue import Empty

import base64
import json
import logging
import logging.config
import requests
from requests import ConnectionError
import setproctitle
import socket
import urllib2
import urlparse

import Asterisk
from Asterisk.Manager import Manager
import odoorpc

from conf import *

logging.config.dictConfig(LOGGING)
_logger = logging.getLogger(__file__)

odoo = None
greenlet_handles = [] # Handles for spawned greenlets
server_ami_managers = []

def get_odoo_connection():
    while True:
        try:
            odoo = odoorpc.ODOO(ODOO_HOST, port=ODOO_PORT)
            odoo.login(ODOO_DB, ODOO_USER, ODOO_PASSWORD)
            _logger.info('Connected to Odoo.')
            return odoo
        except urllib2.URLError as e:
            if 'Errno 61' in str(e):  # Connection refused
                _logger.error('Cannot connect to Odoo, trying again.')
                gevent.sleep(ODOO_RECONNECT_TIMEOUT)
            else:
                raise



class ServerAmiManager(object):
    #cmd_Q = Queue()

    def __init__(self, server_id, host, port, username, password):
        self.server_id = server_id
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        # Start the command Q
        # Populate events
        self.events = Asterisk.Util.EventCollection()
        self.events.subscribe('VarSet', self.handle_event)
        self.events.subscribe('Hangup', self.handle_event)
        self.events.subscribe('PeerStatus', self.handle_event)
        self.events.subscribe('Newchannel', self.handle_event)
        self.events.subscribe('NewExten', self.handle_event)
        self.events.subscribe('NewConnectedLine', self.handle_event)
        self.events.subscribe('Newstate', self.handle_event)


    def register(self, pbx):
        pbx.events += self.events


    def unregister(self, pbx):
        pbx.events -= self.events


    def handle_event(self, pbx, event):
        # General method to spawn event handlres.
        # Search for method named on_EventName
        event_handler = getattr(self, 'on_{}'.format(event.get('Event')), None)
        if event_handler:
            gevent.spawn(event_handler, pbx, event)

    """
    def handle_cmd_Q(self):
        while True:
            try:
                msg = self.cmd_Q.get_nowait()
            except Empty:
                gevent.sleep(1)
                continue
            command = msg.get('command')
            method = getattr(self, 'command_' + command, None)
            if method:
                _logger.debug('Q got {}'.format(method))
                method(msg)
            else:
                _logger.error('Method {} not found.'.format(command))
            gevent.sleep(1)
    """


    def loop(self):
        while True:
            try:
                # Create PBX connection
                self.pbx = Manager((self.host, int(self.port)),
                                   self.username, self.password)
                _logger.info('Connected to {}'.format(self.host))
                self.register(self.pbx)
                self.pbx.serve_forever()
            except socket.error as e:
                _logger.error('Server {} socket error: {}.'.format(
                    self.host, e.strerror))
            except Asterisk.BaseException as e:
                _logger.error('Server {} error, {}.'.format(
                    self.host, e))
            except ConnectionError as e:
                _logger.error('Server {} connection error, {}.'.format(
                    self.host, e))
            except:
                raise
            _logger.info(
                'Reconnecting in {} seconds...'.format(AMI_RECONNECT_TIMEOUT))
            gevent.sleep(AMI_RECONNECT_TIMEOUT)


    def update_qos(self, pbx, event):
        # We have to give CDR some time to get into the database.
        # Odoo may not complete a WEB transaction so no record will be found to update.
        gevent.sleep(UPDATE_CDR_DELAY)
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
        return odoo.env['asterisk.cdr'].update_qos(values)


    def update_channel_state(self, pbx, event):
        gevent.sleep(UPDATE_CHANNEL_DELAY)
        # Take the Channel from the message to make it serializable.
        channel = event.pop('Channel')
        event['Channel'] = '{}'.format(channel)
        return odoo.env['asterisk.channel'].update_channel_state(event)


    def hangup_channel(self, pbx, event):
        gevent.sleep(UPDATE_CHANNEL_DELAY)
        # Take the Channel from the message to make it serializable.
        channel = event.pop('Channel')
        event['Channel'] = '{}'.format(channel)
        return odoo.env['asterisk.channel'].hangup_channel(event)


    def get_call_recording(pbx, event):
        _logger.debug('Get call recording.')
        # Make a delay to let Asterisk close recorded file.
        gevent.sleep(RECORDING_DOWNLOAD_DELAY)
        call_id = event.get('Uniqueid')
        exten = event.get('Exten')
        # Download recording
        url = 'http://{}:{}/static/monitor/{}.wav'.format(
            conf['host'], conf['http_port'], call_id)
        response = requests.get(url)
        if response.status_code == 404:
            _logger.info('Recording for {} not found on the server.'.format(exten))
        elif response.status_code == 200:
            _logger.debug('Recording found, process.')
            file_data = response.content
            upload_complete = False
            try:
                result = odoo.env['asterisk.cdr'].save_call_recording(
                    call_id, base64.encodestring(file_data))
                if not result:
                    _logger.error('Odoo save_call_recording result is False.')
                else:
                    _logger.debug('Call recording saved.')
                    upload_complete = True
            except odoorpc.error.RPCError as e:
                _logger.error('Odoo error: {}'.format(e.message))
            # Delete recording
            url = urlparse.urljoin(ASTERISK_HELPER_URL,
                          '/delete_recording?filename={}.wav'.format(call_id))
            _logger.debug('Calling {}'.format(url))
            response = requests.get(url)
            if response.content != 'DELETED':
                _logger.warning('Bad response: {}'.format(response.content))
        else:
            _logger.warn(
                'Unhandled status code {} received from the server.'.format(
                    response.status_code))


    def on_Hangup(self, pbx, event):
        _logger.debug('on_{}'.format(event.get('Event')))
        # Spawn call recording handling.
        gevent.spawn(self.hangup_channel, pbx, event)
        gevent.spawn(self.get_call_recording, event)


    def on_VarSet(self, pbx, event):
        _logger.debug('on_{}'.format(event.get('Event')))
        # QoS of CDR
        var = event.get('Variable')
        if var == 'RTPAUDIOQOS':
            return self.update_qos(pbx, event)
        else:
            _logger.debug('Ignoring SetVar {}.'.format(var))


    def on_PeerStatus(self, pbx, event):
        _logger.debug('on_{}'.format(event.get('Event')))
        if event.get('ChannelType') == 'SIP':
            # We only care about SIP registrations
            return odoo.env['asterisk.sip_peer_status'].update_status(event)


    def on_Newchannel(self, pbx, event):
        _logger.debug('on_{}'.format(event.get('Event')))
        # Get channel represenation of Channel object.
        channel = event.pop('Channel')
        event['Channel'] = '{}'.format(channel)
        return odoo.env['asterisk.channel'].new_channel(event)


    def on_Newstate(self, pbx, event):
        _logger.debug('on_{}'.format(event.get('Event')))
        return self.update_channel_state(pbx, event)

    def on_NewExten(self, pbx, event):
        _logger.debug('on_{}'.format(event.get('Event')))
        return self.update_channel_state(pbx, event)

    def on_NewConnectedLine(self, pbx, event):
        _logger.debug('on_{}'.format(event.get('Event')))
        return self.update_channel_state(pbx, event)



def poll_message_bus():
    _logger.info('Starting bus poller.')
    # Clear message history
    rec_ids = odoo.env['bus.bus'].search([('channel', '=', '"ami_broker"')])
    odoo.env['bus.bus'].unlink(rec_ids)
    msg_id = 0
    while True:
        try:
            headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
            url = 'http://{}:{}/longpolling/poll'.format(ODOO_HOST, ODOO_POLLING_PORT)
            r = requests.get(url, stream=True, headers=headers, json={
                'params': {
                    'channels': ['ami_broker'],
                    'last': msg_id
                }
            })
            for line in r.iter_lines():
                if line:
                    decoded_line = json.loads(line.decode('utf-8'))
                    result_list = decoded_line.get('result')
                    for result in result_list:
                        msg_id = result.get('id')
                        channel = result.get('channel')
                        _logger.debug(
                            'Message bus channel {}, message {}, id {}.'.format(
                                channel, result.get('message'), msg_id))
                        try:
                            msg = json.loads(result.get('message'))
                        except ValueError:
                            _logger.error('Bad message received: {}'.format(
                                result.get('message')
                            ))
                            continue
                        command = msg.get('command')
                        if command == 'reload':
                            _logger.info('Reloading broker.')
                            for h in greenlet_handles:
                                h.kill()
                            gevent.sleep(AMI_RELOAD_PAUSE)
                            gevent.spawn(spawn_server_ami_managers)

                        else:
                            _logger.error(
                                'Uknown message received from the bus: {}'.format(
                                    msg
                                ))
            continue

        except ConnectionError as e:
            _logger.error('Poll message bus error: {}'.format(e))
            gevent.sleep(POLL_RECONNECT_TIMEOUT)
            continue



def spawn_server_ami_managers():
    servers = odoo.env['asterisk.server'].search([])
    for server_id in servers:
        server = odoo.env['asterisk.server'].browse(server_id)[0]
        manager = ServerAmiManager(server.id, server.host, server.ami_port,
                               server.ami_username, server.ami_password)
        server_ami_managers.append(manager)
        try:
            h = gevent.spawn(manager.loop)
            _logger.info('AMI broker for {} has been started.'.format(server.name))
            greenlet_handles.append(h)
        except KeyboardInterrupt, SystemExit:
            _logger.info('AMI broker for {} has been terminated.'.format(server.name))



def start():
    _logger.info('Starting AMI broker...')
    setproctitle.setproctitle('ami_broker')
    global odoo
    odoo = get_odoo_connection()
    # Spawn AMI managers
    spawn_server_ami_managers()
    # Spawn Odoo bus poller
    #greenlet_handles.append()
    gevent.joinall([gevent.spawn(poll_message_bus)])


if __name__ == '__main__':
    start()
