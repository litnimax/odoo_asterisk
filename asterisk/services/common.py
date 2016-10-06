import ari
import base64
import gevent
import logging, logging.config
from PIL import Image
import requests
from requests.exceptions import HTTPError, ReadTimeout, ConnectionError
import socket
from StringIO import StringIO
import time

from conf import *

try:
    from local_conf import *
except ImportError:
    pass


logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(level=logging.DEBUG)


def load_parameters(odoo, params):
    def load_param(param):
        value = odoo.env['ir.config_parameter'].get_param(param, None)
        if value:
            logger.info('Loaded {}.'.format(param))
            return value
        else:
            logger.error('Error loading {}!'.format(param))

    result = {}
    for param in params:
        result[param] = load_param(param)
    return result



def safe_hangup(channel):
    """Hangup a channel, ignoring 404 errors.
    :param channel: Channel to hangup.
    """
    try:
        channel.hangup()
    except HTTPError as e:
        # Ignore 404's, since channels can go away before we get to them
        if e.response.status_code != requests.codes.not_found:
            raise


def quit_stasis(channel, event):
    """Exit to dialplan to the next priority after Stasis was called
    :param channel: Channel to exit
    """
    try:
        channel.continueInDialplan(
            context=event['channel']['dialplan']['context'],
            extension=event['channel']['dialplan']['exten'],
            priority=event['channel']['dialplan']['priority'] + 1
        )
    except HTTPError as e:
        # Ignore 404's, since channels can go away before we get to them
        if e.response.status_code != requests.codes.not_found:
            raise

def continue_dialplan(channel, event,
                      context=None, extension=None,priority=None):
    """Exit to dialplan the specified context / exten / priority
    :param channel: Channel to exit
    """
    try:
        channel.continueInDialplan(
            context=context or event['channel']['dialplan']['context'],
            extension=extension or event['channel']['dialplan']['exten'],
            priority=priority or 1
        )
    except HTTPError as e:
        # Ignore 404's, since channels can go away before we get to them
        if e.response.status_code != requests.codes.not_found:
            raise


def connect_ari(conf):
    try:
        ari_client = ari.connect(
            str(conf['barrier_pbx_ari_url']),
            str(conf['barrier_pbx_ari_user']),
            str(conf['barrier_pbx_ari_password']),
        )
        logger.info('Connected to ARI at {}.'.format(
            conf['barrier_pbx_ari_url']))
        return ari_client

    except HTTPError as e:
        if e.response.status_code == 503:
            logger.error('Cannot connect to Asterisk WebSocket. Try again.')

    except ConnectionError:
        logger.error('Max retries exceeded connecting to Asterisk WebSocket. Try again.')

    except ReadTimeout:
        logger.error('Read timeout connecting to Asterisk WebSocket. Try again.')

    except socket.error as e:
        logger.error('Socket error. Try again.')



def create_entry_log(odoo, barrier=None, access_object=None, result=None,
                     number=None, result_message=None):

    resident = access_object.resident if access_object else None
    facility = barrier.facility if barrier else None

    return odoo.env['barrier.entry_log'].create({
        'event_number': number,
        'event_type': 'phone',
        'result': result,
        'result_message': result_message,
        'resident': resident.id if resident else None,
        'resident_name': resident.name if resident else None,
        'barrier': barrier.id if barrier else None,
        'barrier_uid': barrier.uid if barrier else None,
        'facility': facility.id if facility else None,
        'facility_name': facility.name if facility else None,
    })



def save_entry_picture(odoo, entry_id):
    logger.debug('Going to save picture for entry {}.'.format(entry_id))
    entry_log = None
    try:
        entry_log = odoo.env['barrier.entry_log'].browse(entry_id)
    except ValueError as e:
        if 'There is no' in e.message:
            logger.warning('Could not find entry log {}, '
                           'trying in 5 seconds.'.format(entry_id))
            gevent.sleep(5)
            try:
                entry_log = odoo.env['barrier.entry_log'].browse(entry_id)
            except ValueError as e:
                if 'There is no' in e.message:
                    logger.warning('Still did not find entry log {}, '
                                   'give up.'.format(entry_id))
                    return

    # We have entry log in database
    barrier = entry_log.barrier

    def save_picture():
        if barrier and barrier.camera_url:
            try:
                start = time.time()
                r = requests.get(barrier.camera_url, stream=True,
                                 timeout=PICTURE_SAVE_TIMEOUT)
                if r.status_code == 200:
                    i = Image.open(StringIO(r.content))
                    buffer = StringIO()
                    i.save(buffer, format='JPEG')
                    entry_log.write({
                        'picture': base64.encodestring(buffer.getvalue()),
                        'has_picture': True,
                    })
                    end = time.time()
                    logger.info('Picture for {} saved in {} seconds.'.format(
                        barrier.uid, end - start
                    ))
                    return True
                else:
                    raise Exception('Bad status code: %s' % r.status_code)

            except Exception as e:
                logger.error('Could not get picture: %s' % e)
                entry_log.write({
                    'picture_error': '%s' % str(e),
                    'is_picture_error': True,
                })

    return save_picture()

