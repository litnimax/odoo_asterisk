import logging
logging.basicConfig()
_logger = logging.getLogger(__name__)

PORT = 8010
ASTERISK = '/usr/sbin/asterisk'
ASTERISK_ARGS = '-cr'
ASTERISK_RECORDING_FOLDER = '/var/spool/asterisk/monitor'

SSL_ENABLED = False
SSL_CERT = './cert.pem'
SSL_KEY = './privkey.pem'

try:
    from local_conf import *
except ImportError:
    _logger.warning('No local_conf.py found or import error!')
