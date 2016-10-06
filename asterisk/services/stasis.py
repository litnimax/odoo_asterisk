#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

import ari
import gevent
from gevent.monkey import patch_all; patch_all()
import logging
import odoorpc
import urllib2
from websocket import WebSocketConnectionClosedException

from common import load_parameters, connect_ari, create_entry_log, \
    save_entry_picture, safe_hangup, quit_stasis, continue_dialplan


from conf import *


LOGGING['loggers'].update({
    __name__: {
        'handlers': ['console', 'file'] if LOG_CONSOLE else ['file'],
        'level': LOG_LEVEL,
        'propagate': False,
        }})

logging.config.dictConfig(LOGGING)
logger = logging.getLogger(__name__)


# Here is what we need in this application
conf_parameters = [
    'barrier_pbx_ari_url',
    'barrier_pbx_ari_user',
    'barrier_pbx_ari_password'
]

"""
def playback_and_hangup(channel, event, playback_file_list):
    sounds_folder = 'barrier'
    for file in playback_file_list:
        logger.info('Playing {}/{} to {}'.format(
            sounds_folder, file, event['channel']['caller']['number']))
    safe_hangup(channel)
"""


def access_request(channel, event):
    try:
        # Here we handle calls from users who open barrier from their GSM phones
        called = event['channel']['dialplan']['exten']
        caller = event['channel']['caller']['number']

        # Check access phone number
        access_phone_id = odoo.env['barrier.access_phone'].search([
            ('number', '=', called)
        ])
        if not access_phone_id:
            logger.info('Access phone number {} not found.'.format(called))
            entry_log_id = create_entry_log(odoo, number=caller, result='access_number_not_found',
                             result_message='No access number {}'.format(
                                 called))
            continue_dialplan(channel, event,
                              extension='access_number_not_found')
            return

        # Search access number
        access_number_id = odoo.env['barrier.access_phone_number'].search([
                                ('number', '=', caller),
                                ('access_phone', '=', access_phone_id)])

        if not access_number_id:
            logger.info('Number {} not found in access numbers.'.format(caller))
            entry_log_id = create_entry_log(odoo, result='number_not_found', number=caller)
            playback_and_hangup(channel, event,
                                extension='calling_number_not_found')
            return

        access_number = odoo.env['barrier.access_phone_number'].browse(
            access_number_id)
        barrier = access_number.barrier

        # Check that number is not disabled
        if access_number.is_disabled:
            logger.info('Number {} is disabled.'.format(caller))
            entry_log_id = create_entry_log(
                odoo, barrier=barrier, result='number_disabled',
                access_object=access_number, number=caller)
            gevent.spawn(save_entry_picture, entry_log_id)
            continue_dialplan(channel, event,
                              extension='calling_number_is_disabled')
            return

        # Check bans
        if odoo.env['barrier.ban'].is_banned(caller, barrier.id):
            logger.info('Number {} is banned.'.format(caller))
            entry_log_id = create_entry_log(odoo, barrier=barrier,
                                            result='banned',
                                            access_object=access_number,
                                            number=caller)
            gevent.spawn(save_entry_picture, entry_log_id)
            continue_dialplan(channel, event, extension='caller_is_banned')
            return

        # Check that barrier accepts event
        if not barrier.accept_phones:
            logger.info('Barrier {} does not accept phones.'.format(barrier.uid))
            entry_log_id = create_entry_log(odoo, barrier=barrier,
                                            result='event_not_accepted',
                                            access_object=access_number,
                                            number=caller)
            gevent.spawn(save_entry_picture, entry_log_id)
            continue_dialplan(channel, event,
                              extension='phones_are_not_accepted')
            return

        # Finally we accept
        entry_log_id = create_entry_log(odoo, barrier=barrier, result='accepted',
                                     access_object=access_number,
                                     number=caller)
        gevent.spawn(save_entry_picture, odoo, entry_log_id)
        logger.info('Accepting access from {} to {}, entry {}.'.format(
            caller, barrier.uid, entry_log_id))
        # Hangup caller as we don't play him anything
        safe_hangup(channel)
        result = odoo.env['barrier.barrier'].open_barrier_from_stasis(
            barrier.id, entry_log_id=entry_log_id)
        if result is False:
            logger.warning('Could not open barrier {} for entry {}.'.format(
                barrier.uid, entry_log_id))

    except Exception as e:
        logger.exception('Error on access_request, quitting Stasis.')
        quit_stasis(channel, event)



def search_call_panel_or_resident(channel, event):
    caller = event['channel']['caller']['number']
    barrier_id = odoo.env['barrier.barrier'].search(['|',
        ('call_panel_sip_number', '=', caller),
        ('call_panel_gsm_number', '=', caller)])
    if barrier_id:
        barrier = odoo.env['barrier.barrier'].browse(barrier_id)
        logger.info(u'Call Panel {}.'.format(barrier.name))
        name = u'{} {}'.format(barrier.description, barrier.facility.address)
        channel.setChannelVar(variable='CALLERID(name)',
                              value=name.encode('utf-8'))
        continue_dialplan(channel, event, extension='callpanel')
    else:
        logger.info('Call Panel not found for {}. Trying search a resident...'.format(caller))
        phone_ids = odoo.env['barrier.resident_info_phone'].search([
            ('number', '=', caller)])
        if phone_ids:
            names = []
            for phone_id in phone_ids:
                phone = odoo.env['barrier.resident_info_phone'].browse(phone_id)
                names.append(phone.resident.name)
            logger.info(u'Found resident(s) {}.'.format(u','.join(names)))
            channel.setChannelVar(variable='CALLERID(name)',
                                  value=u';'.join(names)[:80].encode('utf-8'))
            continue_dialplan(channel, event, extension='resident')

        else:
            logger.info('Resident not found for {}.'.format(caller))
            continue_dialplan(channel, event, extension='notfound')



def on_start(channel_dict, event):
    #import json
    #print json.dumps(event, indent=4)
    channel = channel_dict.get('channel')
    caller = event['channel']['caller']['number']
    called = event['channel']['dialplan']['exten']
    channel.setChannelVar(variable='FROM_NUMBER', value=caller)
    channel.setChannelVar(variable='TO_NUMBER', value=called)
    args = event['args']
    # Remember where call entered Stasis app
    dialplan = event['channel']['dialplan']
    logger.info('Call from {} to {}.'.format(caller, called))
    try:
        # Check if this call is GSM key call.
        if 'access_request' in args:
            logger.info('Access request call from {}.'.format(caller))
            gevent.spawn(access_request, channel, event)
            return

        if 'call_panel_or_resident' in args:
            logger.debug('Search call panel or resident for {}.'.format(caller))
            gevent.spawn(search_call_panel_or_resident, channel, event)
            return

        # Nothing found, just exit to dialplan
        logger.error('Stasis args not found!')
        channel.continueInDialplan(context=dialplan['context'],
                                   extension='error',
                                   priority=1)

    except Exception as e:
        logger.exception('Unhandled error:')
        channel.continueInDialplan(context=dialplan['context'],
                                   extension='error',
                                   priority=1)


def always_connect_ari(conf):
    while True:
        ari_client = connect_ari(conf)
        if ari_client:
            try:
                ari_client.on_channel_event('StasisStart', on_start)
                ari_client.run(apps=STASIS_APP)

            except WebSocketConnectionClosedException as e:
                logger.error('WebSocket connection is closed. Exit.')

            except ValueError: # ari_client.run(apps='barrier'): No JSON object could be decoded
                logger.error('ValueError on connect_ari. Restarting.')

        else:
            gevent.sleep(ARI_RECONNECT_TIMEOUT)
            continue



def get_odoo_connection():
    while True:
        try:
            odoo = odoorpc.ODOO(ODOO_HOST, port=ODOO_PORT)
            odoo.login(ODOO_DB, ODOO_USER, ODOO_PASSWORD)
            logger.info('Connected to Odoo.')
            return odoo
        except urllib2.URLError as e:
            if 'Errno 61' in str(e):  # Connection refused
                logger.error('Cannot connect to Odoo, trying again.')
                gevent.sleep(ODOO_RECONNECT_TIMEOUT)
            else:
                raise



if __name__ == '__main__':
    logger.info('Barrier stasis app has been started.')
    odoo = get_odoo_connection()
    conf = load_parameters(odoo, conf_parameters)
    ari_handle = gevent.spawn(always_connect_ari, conf)
    try:
        gevent.joinall([ari_handle])
    except (KeyboardInterrupt, SystemExit):
        logger.info('Terminating.')
