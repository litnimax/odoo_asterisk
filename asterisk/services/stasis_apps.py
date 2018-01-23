#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# Patch all before other imports!
import gevent
from gevent.monkey import patch_all; patch_all()
from gevent.event import Event

import ari
import json
import logging
import logging.config
import os
import requests
import time
from requests.exceptions import HTTPError, ReadTimeout, ConnectionError
import setproctitle
import socket
import urllib2
from urlparse import urljoin
from websocket import WebSocketConnectionClosedException

import odoorpc

STASIS_APP = 'odoo'

odoo = None # Global instance of odoo connection shared by all greenlets.
ari_client = None # Global instance of ARI client

ODOO_HOST = os.environ.get('ODOO_IP', 'odoo')
ODOO_PORT = int(os.environ.get('ODOO_PORT', '8069'))
ODOO_DB = os.environ.get('ODOO_DB', 'asterisk')
ODOO_USER = os.environ.get('ODOO_USER', 'admin')
ODOO_PASSWORD = os.environ.get('ODOO_PASSWORD', 'admin')
ODOO_RECONNECT_TIMEOUT = int(os.environ.get('ODOO_RECONNECT_TIMEOUT', '5'))
ARI_RECONNECT_TIMEOUT = int(os.environ.get('ARI_RECONNECT_TIMEOUT', '5'))
HTTP_LISTEN_ADDRESS = os.environ.get('HTTP_LISTEN_ADDRESS', '127.0.0.1')
HTTP_PORT = int(os.environ.get('HTTP_PORT', '8088'))
HTTP_LOGIN = os.environ.get('MANAGER_LOGIN', 'odoo')
HTTP_PASSWORD = os.environ.get('MANAGER_PASSWORD', 'odoo')


# Configure logger
logging.basicConfig(level=logging.DEBUG)


def continue_dialplan(channel, event,
                      context=None, extension=None,priority=None):
    """
    Exit to dialplan the specified context / exten / priority.
    """
    try:
        channel.continueInDialplan(
            context=context or event['channel']['dialplan']['context'],
            extension=extension or event['channel']['dialplan']['exten'],
            priority=priority or event['channel']['dialplan']['priority'] + 1
        )
    except HTTPError as e:
        # Ignore 404's, since channels can go away before we get to them
        if e.response.status_code != requests.codes.not_found:
            raise


def connect_to_context(channel, event):
    try:
        result = channel.getChannelVar(variable='CONNECT_TO_CONTEXT')
        context_exten = result.get('value')
        if context_exten:
            logging.debug('ari_app_connect_to_context, redirect to %s'
                                                            % context_exten)
            extension, context = context_exten.split('@')
            channel.continueInDialplan(context=context, extension=extension, priority=1)
        else:
            logging.error('ari_app_connect_to_context, no exten@context passed!')

    except HTTPError as e:
        if e.response.status_code == requests.status_codes.codes.not_found:
            logging.warning('Channel not found!')
    except Exception as e:
        logging.error('Error: %s' % e)


def originate(**kwargs):
    if not ari_client:
        return {'status': 'error', 'message': 'ARI not connected'}
    endpoint=kwargs.get('endpoint')
    context=kwargs.get('context', 'default')
    exten=kwargs.get('exten', 's')
    priority=kwargs.get('priority', 1)
    callerid=kwargs.get('callerid', '')
    variables=kwargs.get('variables', {})
    timeout=kwargs.get('timeout', ARI_ORIGINATE_TIMEOUT)
    logging.info('Originate {} from {} to {}@{},{}'.format(
        endpoint, callerid, exten, context, priority))
    evt = Event()  # Wait flag for origination
    result = {}
    try:
        # Sanitarize variables
        for k,v in variables.items():
            if not v:
                logging.warning('Popping empty variable {}'.format(k))
                variables.pop(k)

        start_time = time.time()
        variables.update({
            'CONNECT_TO_CONTEXT': '{}@{}'.format(exten, context)})
        channel = ari_client.channels.originate(
            endpoint=endpoint,
            app=STASIS_APP,
            appArgs='connect_to_context',
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
                result['duration'] = '%0.2f' % (stop_time - start_time)

                if state == 'Up' and cause in ['16']:
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
                logging.exception('Error on destroyed!')

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
        logging.exception('Originate ARI error!')
        result['status'] = 'error'
        result['message'] = e.message

    finally:
        logging.debug('Call to %s status: %s (%s).' % (endpoint,
            result['status'], result['message']))
        return result



def set_callerid(channel, event):
    global odoo
    caller = event['channel']['caller']['number']
    called = event['channel']['dialplan']['exten']
    app_args = ','.join(event['args'])
    app = event['application']
    try:
        # Search contacts first. If there is more then one contact found we take
        # only company name. Of only one contact is found we set caller id
        # as Arthur Gomez (AsusTek). If not contacts are found we search companies
        # with numbers set.
        found = odoo.env['res.partner'].search([
            ('is_company', '=', False),
            '|',
            ('phone', '=', caller),
            ('mobile', '=', caller)])
        if len(found) == 1:
            # One contact found
            contact = odoo.env['res.partner'].browse(found)[0]
            if contact.parent_name:
                # Add also contact's company name.
                logging.info(u'Found {} from {}.'.format(
                    contact.name, contact.parent_name))
                name = '{} ({})'.format(contact.name, contact.parent_name)
            else:
                logging.info(u'Found {}.'.format(contact.name))
                name = contact.name
            channel.setChannelVar(variable='CALLERID(name)',
                                  value=name.encode('utf-8'))
        elif len(found) > 1:
            # Many contacts found
            name = odoo.env['res.partner'].browse(found)[0].parent_name
            logging.info(u'Found many contacts, setting company name {}.'.format(name))
            channel.setChannelVar(variable='CALLERID(name)',
                                  value=name.encode('utf-8'))
        else:
            logging.info('No contacts found for {}.'.format(caller))
        # Exit Stasis app.
        continue_dialplan(channel, event)

    except HTTPError as e:
        if e.response.status_code == 404:
            # ARI error, channel was hangup.
            logging.warning(
                'Channel disconnected from Stasis by Asterisk. Stasis: {}({}), '\
                'channel: {}, called: {}, calling: {}'.format(
                    app, app_args, channel_id, called, caller))

    except Exception as e:
        logging.exception('Error on search_call_panel_or_resident, quitting Stasis.')
        continue_dialplan(channel, event, extension='stasis-error')



def on_stasis_start(channel_dict, event):
    channel = channel_dict.get('channel')
    caller = event['channel']['caller']['number']
    called = event['channel']['dialplan']['exten']
    app_args = ','.join(event['args'])
    app = event['application']
    channel_id = event['channel']['id']
    try:
        #import json; print json.dumps(event, indent=4)
        channel.setChannelVar(variable='FROM_NUMBER', value=caller)
        channel.setChannelVar(variable='TO_NUMBER', value=called)
        # Remember where call entered Stasis app
        dialplan = event['channel']['dialplan']
        logging.info('Call from {} to {}.'.format(caller, called))
        # Check if this call is GSM key call.
        if 'set_callerid' in app_args:
            logging.info('Set callerid for {}.'.format(caller))
            gevent.spawn(set_callerid, channel, event)
            return
        elif 'connect_to_context' in app_args:
            logging.info('Connecting {} to exten {}.'.format(caller, called))
            return gevent.spawn(connect_to_context, channel, event)


        # Nothing found, just exit to dialplan
        logging.error('Stasis args not found!')
        continue_dialplan(channel, event)

    except HTTPError as e:
        if e.response.status_code == 404:
            # ARI error, channel was hangup.
            logging.warning(
                'Channel disconnected from Stasis by Asterisk. Stasis: {}({}), '\
                'channel: {}, called: {}, calling: {}'.format(
                    app, app_args, channel_id, called, caller))

    except Exception as e:
        logging.error('Unhandled error: {}'.format(e))
        continue_dialplan(channel, event, extension='stasis-error')



def connect_ari():
    try:
        if not odoo:
            raise Exception('Odoo not connected.')
        # Connect only to one server for now :-P
        url = 'http://{}:{}'.format(HTTP_LISTEN_ADDRESS, HTTP_PORT)
        logging.debug('ARI connecting to {} as {}:{}'.format(
            url, HTTP_LOGIN, HTTP_PASSWORD))
        ari_client = ari.connect(url, HTTP_LOGIN, HTTP_PASSWORD)
        if not ari_client:
            logging.error('ARI client not connected.')
            return False
        else:
            logging.info('Connected to ARI.')
            return ari_client

    except HTTPError as e:
        logging.error('Cannot connect to Asterisk WebSocket: {}'.format(e.message))


    except ConnectionError:
        logging.error('Max retries exceeded connecting to Asterisk WebSocket. Try again.')

    except ReadTimeout:
        logging.error('Read timeout connecting to Asterisk WebSocket. Try again.')

    except socket.error as e:
        logging.error('Socket error. Try again.')



def always_connect_ari():
    while True:
        global ari_client
        ari_client = connect_ari()
        if ari_client:
            try:
                ari_client.on_channel_event('StasisStart', on_stasis_start)
                ari_client.run(apps=STASIS_APP)

            except WebSocketConnectionClosedException as e:
                logging.error('WebSocket connection is closed. Exit.')

            except ValueError: # ari_client.run(apps='barrier'): No JSON object could be decoded
                logging.error('ValueError on connect_ari. Restarting.')

            except socket.error as e:
                if e.errno == 60:
                    logging.error('Operation timed out, reconnecting.')

        else:
            logging.debug('Sleeping {} on ARI reconnect.'.format(ARI_RECONNECT_TIMEOUT))
            gevent.sleep(ARI_RECONNECT_TIMEOUT)
            continue



def get_odoo_connection():
    while True:
        try:
            odoo = odoorpc.ODOO(ODOO_HOST, port=ODOO_PORT)
            odoo.login(ODOO_DB, ODOO_USER, ODOO_PASSWORD)
            logging.info('Connected to Odoo.')
            return odoo
        except urllib2.URLError as e:
            if 'Errno 61' in str(e):  # Connection refused
                logging.error('Cannot connect to Odoo, trying again.')
                gevent.sleep(ODOO_RECONNECT_TIMEOUT)
            else:
                raise



def start():
    logging.info('Stasis app {} has been started.'.format(STASIS_APP))
    setproctitle.setproctitle('stasis_{}'.format(STASIS_APP))
    global odoo
    odoo = get_odoo_connection()
    ari_handle = gevent.spawn(always_connect_ari)
    try:
        gevent.joinall([ari_handle])
    except (KeyboardInterrupt, SystemExit):
        logging.info('Terminating.')


if __name__ == '__main__':
    start()
