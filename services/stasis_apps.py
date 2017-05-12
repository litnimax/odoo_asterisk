#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# Patch all before other imports!
import gevent
from gevent.monkey import patch_all; patch_all()

import ari
import logging
import logging.config
import odoorpc
from requests.exceptions import HTTPError, ReadTimeout, ConnectionError
import setproctitle
import socket
import urllib2
from urlparse import urljoin
from websocket import WebSocketConnectionClosedException

STASIS_APP = 'odoo'

odoo = None # Global instance of odoo connection shared by all greenlets.

# Import default cpnfiguration.
from conf import *

# Configure logger
logging.config.dictConfig(LOGGING)
_logger = logging.getLogger(__file__)


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
                _logger.info(u'Found {} from {}.'.format(
                    contact.name, contact.parent_name))
                name = '{} ({})'.format(contact.name, contact.parent_name)
            else:
                _logger.info(u'Found {}.'.format(contact.name))
                name = contact.name
            channel.setChannelVar(variable='CALLERID(name)',
                                  value=name.encode('utf-8'))
        elif len(found) > 1:
            # Many contacts found
            name = odoo.env['res.partner'].browse(found)[0].parent_name
            _logger.info(u'Found many contacts, setting company name {}.'.format(name))
            channel.setChannelVar(variable='CALLERID(name)',
                                  value=name.encode('utf-8'))
        else:
            _logger.info('No contacts found for {}.'.format(caller))
        # Exit Stasis app.
        continue_dialplan(channel, event)

    except HTTPError as e:
        if e.response.status_code == 404:
            # ARI error, channel was hangup.
            _logger.warning(
                'Channel disconnected from Stasis by Asterisk. Stasis: {}({}), '\
                'channel: {}, called: {}, calling: {}'.format(
                    app, app_args, channel_id, called, caller))

    except Exception as e:
        _logger.exception('Error on search_call_panel_or_resident, quitting Stasis.')
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
        _logger.info('Call from {} to {}.'.format(caller, called))
        # Check if this call is GSM key call.
        if 'set_callerid' in app_args:
            _logger.info('Set callerid for {}.'.format(caller))
            gevent.spawn(set_callerid, channel, event)
            return

        # Nothing found, just exit to dialplan
        _logger.error('Stasis args not found!')
        continue_dialplan(channel, event)

    except HTTPError as e:
        if e.response.status_code == 404:
            # ARI error, channel was hangup.
            _logger.warning(
                'Channel disconnected from Stasis by Asterisk. Stasis: {}({}), '\
                'channel: {}, called: {}, calling: {}'.format(
                    app, app_args, channel_id, called, caller))

    except Exception as e:
        _logger.exception('Unhandled error:')
        continue_dialplan(channel, event, extension='stasis-error')



def connect_ari(conf):
    try:
        url = 'http://{}:{}'.format(conf['host'], conf['http_port'])
        _logger.debug('ARI connecting to {}'.format(url))
        ari_client = ari.connect(url, conf['ari_username'], conf['ari_password'])
        if not ari_client:
            _logger.error('ARI client not connected.')
            return False
        else:
            _logger.info('Connected to ARI.')
            return ari_client

    except HTTPError as e:
        _logger.error('Cannot connect to Asterisk WebSocket: {}'.format(e.message))


    except ConnectionError:
        _logger.error('Max retries exceeded connecting to Asterisk WebSocket. Try again.')

    except ReadTimeout:
        _logger.error('Read timeout connecting to Asterisk WebSocket. Try again.')

    except socket.error as e:
        _logger.error('Socket error. Try again.')



def always_connect_ari(conf):
    while True:
        ari_client = connect_ari(conf)
        if ari_client:
            try:
                ari_client.on_channel_event('StasisStart', on_stasis_start)
                ari_client.run(apps=STASIS_APP)

            except WebSocketConnectionClosedException as e:
                _logger.error('WebSocket connection is closed. Exit.')

            except ValueError: # ari_client.run(apps='barrier'): No JSON object could be decoded
                _logger.error('ValueError on connect_ari. Restarting.')

            except socket.error as e:
                if e.errno == 60:
                    _logger.error('Operation timed out, reconnecting.')

        else:
            _logger.debug('Sleeping {} on ARI reconnect.'.format(ARI_RECONNECT_TIMEOUT))
            gevent.sleep(ARI_RECONNECT_TIMEOUT)
            continue



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


def start():
    _logger.info('Stasis app {} has been started.'.format(STASIS_APP))
    setproctitle.setproctitle('stasis_{}'.format(STASIS_APP))
    global odoo
    odoo = get_odoo_connection()
    ari_handle = gevent.spawn(always_connect_ari, conf)
    try:
        gevent.joinall([ari_handle])
    except (KeyboardInterrupt, SystemExit):
        _logger.info('Terminating.')


if __name__ == '__main__':
    start()
