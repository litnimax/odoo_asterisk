# Patch all before importing other modules!
import gevent
from gevent.monkey import  patch_all; patch_all()

import base64
import logging
import logging.config
import setproctitle
import urllib2
import urlparse

import Asterisk
from Asterisk.Manager import Manager
import requests
import odoorpc

from conf import *

logging.config.dictConfig(LOGGING)
_logger = logging.getLogger(__file__)

odoo = None


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


def handle_peer_status_message(message):
    _logger.debug(message)
    odoo.env['asterisk.sip_peer_status'].log_status(message)



def handle_qos_message(message):
    # We have to give CDR some time to get into the database.
    # Odoo may not complete a WEB transaction so no record will be found to update.
    gevent.sleep(UPDATE_CDR_DELAY)
    _logger.debug(message)
    odoo.env['asterisk.cdr'].log_qos(message)


def handle_new_channel_message(message):
    _logger.debug('New Channel: {}'.format(message))
    # Take the Channel from the message to make it serializable.
    channel = message.pop('Channel')
    message['Channel'] = '{}'.format(channel)
    odoo.env['asterisk.channel'].new_channel(message)


def handle_new_channel_state_message(message):
    _logger.debug('Channel State {}: {}'.format(message.get('Event'), message))
    gevent.sleep(UPDATE_CHANNEL_DELAY)
    # Take the Channel from the message to make it serializable.
    channel = message.pop('Channel')
    message['Channel'] = '{}'.format(channel)
    odoo.env['asterisk.channel'].new_channel_state(message)


def handle_hangup_channel(message):
    _logger.debug('Hangup Channel: {}'.format(message))
    gevent.sleep(UPDATE_CHANNEL_DELAY)
    # Take the Channel from the message to make it serializable.
    channel = message.pop('Channel')
    message['Channel'] = '{}'.format(channel)
    odoo.env['asterisk.channel'].hangup_channel(message)


def handle_call_recording(pbx, event):
    _logger.debug('Handle recording.')
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




class AmiEvents(object):

    def var_set_event(self, pbx, event):
        # QoS of CDR
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
            gevent.spawn(handle_qos_message, values)


    def peer_status_event(self, pbx, event):
            # QoS of CDR
            if event.get('ChannelType') == 'SIP':
                # We only care about SIP registrations
                gevent.spawn(handle_peer_status_message, event)


    def new_channel_event(self, pbx, event):
        gevent.spawn(handle_new_channel_message, event)


    def new_channel_state_event(self, pbx, event):
        gevent.spawn(handle_new_channel_state_message, event)


    def hangup_event(self, pbx, event):
        _logger.debug('Hangup event.')
        # Spawn call recording handling.
        gevent.spawn(handle_call_recording, pbx, event)
        gevent.spawn(handle_hangup_channel, event)



    def __init__(self):
        self.events = Asterisk.Util.EventCollection()
        self.events.subscribe('VarSet', self.var_set_event)
        self.events.subscribe('Hangup', self.hangup_event)
        self.events.subscribe('PeerStatus', self.peer_status_event)
        self.events.subscribe('Newchannel', self.new_channel_event)
        self.events.subscribe('Newstate', self.new_channel_state_event)
        self.events.subscribe('NewExten', self.new_channel_state_event)
        self.events.subscribe('NewConnectedLine', self.new_channel_state_event)


    def register(self, pbx):
        pbx.events += self.events


    def unregister(self, pbx):
        pbx.events -= self.events


def start():
    _logger.info('Starting AMI broker...')
    setproctitle.setproctitle('ami_broker')
    global odoo
    odoo = get_odoo_connection()
    pbx = Manager((conf['host'],
                        int(conf['ami_port'])),
                        conf['ami_username'],
                        conf['ami_password'])
    ami_events = AmiEvents()
    ami_events.register(pbx)
    try:
        h1 = gevent.spawn(pbx.serve_forever)
        _logger.info('AMI broker has been started.')
        gevent.joinall([h1])
    except KeyboardInterrupt, SystemExit:
        _logger.info('AMI broker has been terminated.')


if __name__ == '__main__':
    start()
