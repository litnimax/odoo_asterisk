#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

import ari
import gevent
from gevent import wsgi
from gevent.monkey import patch_all; patch_all()
from gevent.pool import Group
from gevent.event import Event
from flask import Flask, jsonify, request
import json
import logging
import logging.config
from lxml import etree
import newrelic
import newrelic.agent
import requests
from requests.exceptions import HTTPError, ConnectionError, ReadTimeout
from requests.adapters import HTTPAdapter
import signal
from simplejson import JSONDecodeError
import socket
import time
from urlparse import urljoin
import uuid
from websocket import WebSocketConnectionClosedException
import xmlrpclib
from utils import Asterisk, load_config

from conf import *
try:
    from local_conf import *
except ImportError as e:
    print 'Did not import local_conf: %s' % e


LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s  %(message)s'
        }
    },
    'handlers': {
        'console':{
            'level': LOG_LEVEL,
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
        'file': {
            'level': LOG_LEVEL,
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'verbose',
            'filename': LOG_FILE,
            'maxBytes': 10485760,
            'backupCount': 3
        }
    },
    'loggers': {
        'requests': {
            'handlers': ['file', 'console'],
            'level': 'ERROR',
            'propagate': False,
        },
        'pbx_broker': {
            'handlers': ['console', 'file'] if LOG_CONSOLE else ['file'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
        'pbx_utils': {
            'handlers': ['console', 'file'] if LOG_CONSOLE else ['file'],
            'level': LOG_LEVEL,
            'propagate': False,
        }
    }
}

logging.config.dictConfig(LOGGING)
logger = logging.getLogger('pbx_broker')


ari_client = None
server = None
pool = Group()

app = Flask(__name__)


if NEWRELIC_ENABLED:
    newrelic.agent.initialize('./newrelic.ini')
    relic_app = newrelic.agent.register_application()


ASTERISK_CMD_URL = 'tcp://192.168.56.101:1967'

conf = {}
conf['pbx_http_server_url'] = 'http://127.0.0.1:50001'
conf['pbx_ari_url'] = '127.0.0.1:8088'
conf['pbx_ari_user'] = 'test'
conf['pbx_ari_password'] = 'test'
conf['pbx_originate_endpoint'] = 'SIP/operator'
conf['pbx_originate_callerid'] = "<100> Max"
conf['pbx_originate_timeout'] = 60 
conf['pbx_originate_wait_after_dtmf'] = 0.5
conf['pbx_originate_wait_before_dtmf'] = 0.5


odoo_session = requests.Session()
odoo_session.mount('http://', HTTPAdapter(
    pool_connections=50,
    pool_maxsize=100)
)

# Get UID on start and re-use it.

def get_odoo_rpc_uid():
    try:
        common = xmlrpclib.ServerProxy('%s/xmlrpc/2/common' % ODOO_URL)
        uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASSWORD, {})
        if not uid:
            logger.error('Did not login to Odoo!')
            return 0
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


class PbxError(Exception):
    status_code = 500

    def __init__(self, message, status_code=None, payload=None):
        Exception.__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload
        logger.error('PBX Error: %s' % message)

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        rv['status'] = 'error'
        return rv


@app.errorhandler(PbxError)
def handle_pbx_error(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response


@app.errorhandler(Exception)
def all_exception_handler(error):
    logger.exception('Unexpected error!')
    response = jsonify({'status': 'error', 'message': str(error)})
    response.status_code = 500
    return response



# Common decorator to check ari connection
def ari_client_check(func):
    def wrapper(*args, **kwargs):
        if not ari_client:
            logger.error('Cannot execute %s, ARI not connected.' % func.__name__)
            raise PbxError(message='ARI client not connected', status_code=503)
        return func(*args, **kwargs)
    return wrapper


@app.route('/config/reload', methods=['POST'])
def reload_config():
    # Reset UID
    ODOO_UID = get_odoo_rpc_uid()
    old_conf = conf.copy()
    load_config(conf, ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASSWORD)
    if (conf.get('pbx_ari_user') != old_conf.get('pbx_ari_user') or
            conf.get('pbx_ari_password') != old_conf.get('pbx_ari_password') or
                conf.get('pbx_ari_url') != old_conf.get('pbx_ari_url')):
                    if ari_client:
                        logger.info('ARI Settings changed, restarting ARI.')
                        ari_client.close()  # Will automatically restart.
    logger.info('Reload settings.')
    return jsonify({'status': 'success', 'message': 'Reloaded'})



@app.route('/command', methods=['POST'])
def asterisk_command(command=None):
    if not command:
        command = request.get_json().get('command')
    logger.debug('Sending AMI command %s.' % command)
    r = asterisk.command(command)
    return jsonify({'status': 'success', 'message': r})



@ari_client_check
@app.route('/device_state_by_exten')
def json_get_device_state_by_exten():
    data = request.get_json()
    if data is None:
        raise PbxError('No JSON data found')
    exten = data.get('exten')
    if exten is None:
        raise PbxError('No number found in JSON data')
    try:
        result = ari_client.deviceStates.get(deviceName='SIP/{}'.format(exten))
        print result
        state = result.json.get('state')
        return jsonify({'status': 'success', 'state': state})
    except HTTPError as e:
        raise PbxError('Device state error: %s' % e.message)


@ari_client_check
@app.route('/endpoint')
def json_get_endpoint():
    data = request.get_json()
    if data is None:
        raise PbxError('No JSON data found')
    print data
    tech = data.get('tech')
    resource = data.get('resource')
    if not tech or not resource:
        raise PbxError('No tech and resource found in JSON data')
    try:
        result = ari_client.endpoints.get(tech=tech, resource=resource)
        print result
        state = result.json.get('state')
        return jsonify({'status': 'success', 'state': state})
    except HTTPError as e:
        raise PbxError('Device state error: %s' % e.message)



@ari_client_check
@app.route('/channel_by_number')
def json_get_channel():
    data = request.get_json()
    if data is None:
        raise PbxError('No JSON data found')
    number = data.get('number')
    if number is None:
        raise PbxError('No number found in JSON data')
    # Let find channel by called number
    channel = asterisk.get_channel_by_to_from(to_number=number, from_number=number)
    if channel:
        channel_id = channel.json['id']
        channel_name = channel.json['name']
        channel_state = channel.json['state']
        return jsonify({'status': 'found',
                        'channel_id': channel_id,
                        'channel_name': channel_name,
                        'channel_state': channel_state})
    else:
        return jsonify({'status': 'not_found'})



@app.route('/send_dtmf_ari', methods=['POST'])
@ari_client_check
def json_send_dtmf():
    # Get dtmf_sequence and channel from JSON
    data = request.get_json()
    if data is None:
        raise PbxError('No JSON found in request!')
    dtmf = data.get('dtmf_sequence')
    if dtmf is None:
        raise PbxError('No dtmf_sequence specified!')
    channel_name = data.get('channel_name')
    channel_id = data.get('channel_id')
    if channel_name is None and channel_id is None:
        raise PbxError('Must specify either channel_name or channel_id')
    # Get active channel
    if not channel_id:
        channels = ari_client.channels.list()
        active_channels = [c for c in channels
                           if c.json['name'].split('-')[0] == channel_name]
        if not active_channels:
            raise PbxError('Channel not found by name %s' % channel_name)
    else:
        # We have channel_id so get the channel
        try:
            c = ari_client.channels.get(channelId=channel_id)
            active_channels = [c]
        except HTTPError as e:
            if e.response.status_code == 404:
                raise PbxError('Did not get channel by id %s' % channel_id)

    for active_channel in active_channels:
        '''
        try:
            active_channel.sendDTMF(dtmf=dtmf, before=DTMF_BEFORE_WAIT,
                                    between=DTMF_BETWEEN_WAIT,
                                    duration=DTMF_DURATION_WAIT,
                                    after=DTMF_AFTER_WAIT)

        except HTTPError as e:
            if e.response.status_code == 409:
                logger.warning('Tried to send DTMF to non-stasis channel %s' %
                                                active_channel.json['name'])
                continue
        '''
        if dtmf:
            logger.debug('Sending DTMF %s' % dtmf)
            asterisk.send_dtmf(active_channel.json.get('name'), dtmf)
            log_id = data.pop('log_id')
            odoo_rpc('barrier.open_log', 'log_stop', [
                                    log_id, 'success',
                                    'DTMF sent',
                                    ], {})

        else:
            logger.warning('DTMF not specified!')

    return jsonify({'status': 'success'})



@app.route('/originate', methods=['POST'])
def json_originate():
    data = request.get_json()
    logger.debug('Originate to %s' % data.get('number'))
    result = log_originate_to_ari(
        call_type=data.get('call_type'),
        endpoint=data.get('endpoint'),
        number=data.get('number'),
        app=data.get('app'),
        variables=data.get('variables'),
        log_id=data.get('log_id'),
        no_simult=data.get('no_simult'),
        callerid='%s' % data.get('callerid', conf['pbx_originate_callerid']),
    )
    return jsonify(result)


def log_originate_to_ari(**kwargs):
    log_id = kwargs.pop('log_id')
    result = originate_to_ari(**kwargs)
    odoo_rpc('barrier.open_log', 'log_stop', [
                            log_id, result.get('status', 'error'),
                            result.get('message', 'No message from originate')
                            ], {})
    return result


@ari_client_check
def originate_to_ari(endpoint='', number='', app='', variables={},
                     callerid='', timeout=None, from_number='', no_simult=True,
                     call_type=None):
    # Check that there is no call in progress
    logger.info('Originate to ari: %s' % endpoint)
    evt = Event()  # Wait flag for origination
    result = {}
    try:
        if no_simult and asterisk.get_channel_by_to_from(client=ari_client,
                                          to_number=number, from_number=from_number):
            logger.warning('Active call to %s found, will not originate!' % number)
            result['status'] = 'error'
            result['message'] = 'Active call found'
            return result

        if not timeout:
            timeout = conf.get('pbx_originate_timeout', 60)

        # Sanitarize variables
        for k,v in variables.items():
            if not v:
                logger.warning('Popping empty variable {}'.format(k))
                variables.pop(k)

        variables.update({
            'TO_NUMBER': number or '',
            'FROM_NUMBER': from_number or '',
        })

        start_time = time.time()
        channel = ari_client.channels.originate(
            endpoint=endpoint,
            app='barrier',
            appArgs=app,
            callerId=callerid,
            timeout=timeout,
            variables={'variables': variables},
        )

        def destroyed(channel, event):
            state = event['channel']['state']
            try:
                cause = str(event.get('cause', 'No cause code'))
                cause_txt = event.get('cause_txt', 'No cause txt')
                stop_time = time.time()
                duration = stop_time - start_time

                if (call_type == 'controller' and state == 'Ringing'
                    and cause in ['17', '19', '21']) or (call_type == 'call_panel'
                            and state == 'Up' and cause in ['16']):
                        # Only these consider successful
                        result['status'] = 'success'
                        result['message'] = '%s (%s) (%s)' % (cause_txt, state, cause)

                elif state == 'Ringing' and cause in ['16']:
                        result['status'] = 'error'
                        if abs(duration - float(conf['pbx_originate_timeout'])) <= 1:
                                result['message'] = 'Call Timeout (Ringing)'
                        else:
                                result['message'] = 'Call Interrupt (Ringing)'
                else:
                    result['status'] = 'error'
                    result['message'] = '%s (%s) (%s)' % (cause_txt, state, cause)


            except Exception as e:
                result['status'] = 'error'
                result['message'] = e.message
                logger.exception('Error on destroyed!')

            finally:
                evt.set()

        channel.on_event('ChannelDestroyed', destroyed)
        # Wait until we get origination result
        evt.wait()

    except HTTPError as e:
        result['status'] = 'error'
        try:
            error = e.response.json().get('error', '')
            result['message'] = error + ' ' + e.response.json().get('message', '')

        except Exception:
            result['message'] = e.response.content

    except Exception as e:
        logger.exception('Originate ATI error!')
        result['status'] = 'error'
        result['message'] = e.message

    finally:
        logger.debug('Call to %s status: %s (%s).' % (endpoint,
            result['status'], result['message']))
        return result



def ari_app_play_dtmf(channel, event):
    """
    :param channel: Channel to send DTMF sequence for opening.
    :return: Return nothing as we analyze cause codes at the 1-st leg.
    """
    try:
        result = channel.getChannelVar(variable='DTMF_SEQUENCE')
        dtmf_sequence = result.get('value')
        if dtmf_sequence is None:
            logger.warning('No DTMF in channel! Nothing to play!')
            return  # Channel will be hangup on finally block

        result = channel.getChannelVar(variable='DTMF_SETTINGS')
        dtmf_settings = result.get('value')
        if dtmf_sequence is None:
            logger.warning('No DTMF settings in channel! Nothing to set!')
            return  # Channel will be hangup on finally block
        # Split DTMF settings
        before, between, duration, after = dtmf_settings.split('|')
        gevent.sleep(float(conf['pbx_originate_wait_before_dtmf']))
        # Set Volume
        result = channel.getChannelVar(variable='ADD_VOLUME')
        add_volume = result.get('value')
        if add_volume != "0":
            channel.setChannelVar(variable='VOLUME(RX,p)=%s' % add_volume)
            channel.setChannelVar(variable='VOLUME(TX,p)=%s' % add_volume)
        gevent.sleep(0.1) # Just in case so that VOLUME will take effect :-)
        # Play DTMF
        channel.sendDTMF(dtmf=dtmf_sequence, before=before,
                                             between=between,
                                             duration=duration,
                                             after=after)
        gevent.sleep(float(conf['pbx_originate_wait_after_dtmf']))


    except HTTPError as e:
        if e.response.status_code == requests.status_codes.codes.not_found:
            logger.warning('ari_play_dtmf: %s' % str(e))

    except Exception as e:
        logger.exception('ari_app_play_dtmf error: %s' % str(e))

    finally:
        try:
            channel.hangup(reason='normal')
        except HTTPError as e:
            if e.response.status_code == requests.status_codes.codes.not_found:
                logger.warning('ari_app_play_dtmf warning, channel not found!')



def ari_app_connect_to_context(channel, event):
    try:
        result = channel.getChannelVar(variable='CONNECT_TO_CONTEXT')
        context_exten = result.get('value')
        if context_exten:
            logger.debug('ari_app_connect_to_context, redirect to %s'
                                                            % context_exten)
            extension, context = context_exten.split('@')
            channel.continueInDialplan(context=context, extension=extension, priority=1)
        else:
            logger.error('ari_app_connect_to_context, no exten@context passed!')


    except HTTPError as e:
        if e.response.status_code == requests.status_codes.codes.not_found:
            logger.warning('Channel not found!')
    except Exception as e:
        logger.exception('Open command call error: %s' % e)



def ari_app_queue(channel, event):
    # Wuala! Odoo call center in 2 days :-) Very fun!
    channel.answer()
    channel.startMoh(mohClass='default')
    data = channel.json
    channel_id = data['id']
    queue_name = event['args'][1] if len(event['args']) > 1 else None
    logger.debug('Channel {} entered {}'.format(channel_id, queue_name))
    queue = odoo_rpc('barrier.queue', 'search',
                     [[('name', '=', queue_name)]], {})
    if queue:
        logger.debug('Found queue {}'.format(queue_name))
        queue = queue[0]
    else:
        logger.error('Did not found queue {}'.format(queue_name))
        channel.hangup(reason='normal')

    odoo_channel = odoo_rpc('barrier.queue_call', 'create', [{
        'caller_number': data['caller']['number'],
        'queue': queue,
        'state': 'waiting',
        'channel_id': channel_id,
        'channel_name': data['name'],
    }], {})


    def on_end(channel, event, channel_id):
        try:
            odoo_rpc('barrier.queue_call', 'unlink', [[channel_id]])
            logger.info('Call {} removed from {}'.format(channel_id, queue_name))

        except Exception as e:
            logger.exception('Queue ooops:')


    channel.on_event('StasisEnd', on_end, odoo_channel)



def ari_app_call_panel_call(channel, event, **kwargs):
    calling_number = channel.json['caller']['number']
    sip_number = odoo_rpc('barrier.barrier', 'search', [
        ('call_panel_sip_number', '=', calling_number)
    ])
    # May be SIP call?
    if sip_number:
        channel.continueInDialplan(context=CALL_PANEL_IN_CONTEXT,
                                   extension='accept',
                                   priority=1)
        return
    # May be CP GSM call




def ari_app_access_request(channel, event):
    calling_number = channel.json['caller']['number']
    called_number = channel.json['dialplan']['exten']
    # Hangup channel as we don't need it anymore!
    try:
        channel.hangup(reason='normal')
    except HTTPError as e:
        if e.response.status_code == 404:
            logger.warning('Channel is already down: %s -> %s' %
                                    (calling_number, called_number))
    except ReadTimeout as e:
        logger.error('ARI read timeout on hangup! Check Asterisk!')
    except ConnectionError as e:
        logger.error('ARI connection error on hangup! Check Asterisk!')

    # Now process request
    try:
        url = urljoin(ODOO_URL, '/barrier/event/pbx')
        r = odoo_session.post(url, timeout=ODOO_CONNECTION_TIMEOUT,
                          headers={'Content-type': 'application/json'},
                          data=json.dumps({'called_number': called_number,
                                           'calling_number': calling_number}))

        if r.status_code != requests.status_codes.codes.ok:
            logger.error('Could not check pbx event: %s' % r.content)
            return

        data = r.json()
        if data is None:
            logger.error('Cannot get JSON from /barrier/event/pbx! Hangup!')
            return  # TODO: We should have some IVR for callers that we have problems?

        result = data.get('result')
        if result is None:
            logger.error('Cannot get result from /barrier/event/pbx! Hangup!')
            return  # TODO: We should have some IVR for callers that we have problems?

        status = result.get('status')
        if status is None:
            logger.error('Cannot get status from /barrier/event/pbx! Hangup!')
            return  # TODO: We should have some IVR for callers that we have problems?


        logger.debug('Handle status %s for %s from %s' % (status, called_number,
                                                           calling_number))
        if status not in ['accepted', 'created']:
            logger.info('Event not accepted: %s' % status)

        elif status == 'accepted' or (status == 'created' and result.get(
                                                        'open_after_create')):
            logger.info('Event %s, opening barrier %s' % (
                                            status, result.get('barrier_id')))
            res = odoo_rpc('barrier.barrier', 'open_barrier_by_uid',
                    [result.get('barrier_id'), result.get('entry_log_id')], {})

            if res is False:
                logger.warning('Ahtung! barrier %s was not open by all means!' %
                                                    result.get('barrier_id'))


    except (JSONDecodeError, AttributeError):
            logger.exception('Could not check pbx event, no json: %s' % r.content)
            return

    except Exception:
        logging.exception('Un-catched exception!')




def on_start(channel_obj, event):
    try:
        args = event.get('args')
        channel = channel_obj.get('channel')
        calling_number = channel.json['caller']['number']
        called_number = channel.json['dialplan']['exten']
        # Check args
        if not args:
            logger.error('No application selected, args: %s' % args)
            channel.hangup(reason='normal')
            return

        method = globals().get('ari_app_%s' % args[0])
        # Check for method
        if not method:
            logger.error('Absent application selected: %s' % args[0])
            channel.hangup(reason='normal')
            return

        logger.info('Call from %s to %s app %s' % (calling_number,
                                                       called_number,
                                                       args[0]))
        gevent.spawn(method, channel, event)


    except Exception as e:
        logger.exception('Error on start: %s' % e)
        raise



def connect_ari():
    while True:
        try:
            global ari_client
            ari_client = ari.connect(
                conf['pbx_ari_url'],
                conf['pbx_ari_user'],
                conf['pbx_ari_password'],
            )
            logger.info('Connected to ARI.')
            ari_client.on_channel_event('StasisStart', on_start)
            ari_client.run(apps='barrier')

        except WebSocketConnectionClosedException as e:
            ari_client = None
            logger.error('WebSocket connection is closed. Exit.')


        except HTTPError as e:
            ari_client = None
            if e.response.status_code == 503:
                logger.error('Cannot connect to Asterisk WebSocket. Trying again.')

        except ConnectionError:
            ari_client = None
            logger.error('Max retries exceeded connecting to Asterisk WebSocket. Trying again.')

        except ReadTimeout:
            ari_client = None
            logger.error('Read timeout connecting to Asterisk WebSocket. Trying again.')

        except socket.error as e:
            ari_client = None
            logger.error('Socket error. Trying again.')

        except ValueError: # ari_client.run(apps='barrier'): No JSON object could be decoded
            ari_client = None
            logger.error('ValueError on connect_ari. Restarting.')

        # Sleep on errors and reconnect
        gevent.sleep(ARI_CONNECT_TIMEOUT)



if __name__ == '__main__':
    logger.info('Started.')
    load_config(conf, ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASSWORD)
    asterisk = Asterisk(
        conf['pbx_ari_url'],
        conf['pbx_ari_user'],
        conf['pbx_ari_password'])
    ari_handle = gevent.spawn(connect_ari)
    host, port = conf['pbx_http_server_url'].replace('http://', '').split(':')
    server = wsgi.WSGIServer((host, int(port)), app)
    server_handle = gevent.spawn(server.serve_forever)
    pool.add(ari_handle)
    pool.add(server_handle)
    try:
        pool.join()
    except (KeyboardInterrupt, SystemExit):
        logger.info('Terminating.')



