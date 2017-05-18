import logging
import os

logging.basicConfig()
_logger = logging.getLogger(__name__)

# DEFAULT CONFIGURATION

ODOO_HOST = 'localhost'
ODOO_PORT = 9069
ODOO_DB = 'odoo10_asterisk'
ODOO_USER = 'admin'
ODOO_PASSWORD = 'admin'
ODOO_RECONNECT_TIMEOUT = 3 # Second
ARI_RECONNECT_TIMEOUT = 3


ASTERISK_HELPER_URL = 'http://localhost:8010'

conf = {
    'host': '192.168.56.102',
    'ami_port': 5038,
    'http_port': 8088,
    'ami_username': 'asterisk_admin',
    'ami_password': 'admin-secret',
    'ari_username': 'asterisk_admin',
    'ari_password': 'admin-secret',
}

UPDATE_CDR_DELAY = 3 # Delay X sec before updating cdr to make sure it's in DB.
UPDATE_CHANNEL_DELAY = 1 # Delay X sec before updating cdr to make sure it's in DB.
RECORDING_DOWNLOAD_DELAY = 1 # Delay to let Asterisk close recorded file.

LOG_CONSOLE = True
LOG_FILE = os.path.join(os.path.dirname(__file__), 'services.log')
LOG_LEVEL = 'DEBUG'


# Log handlers
HANDLRES = []
if LOG_CONSOLE:
    HANDLRES.append('console')
if LOG_FILE:
    HANDLRES.append('file')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        }
    },
    'handlers': {
        'console':{
            'level': LOG_LEVEL,
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
    }
}


# Log to file if log file is configured
if LOG_FILE:
    LOGGING['handlers']['file'] = {
        'level': LOG_LEVEL,
        'class': 'logging.handlers.RotatingFileHandler',
        'formatter': 'verbose',
        'filename': LOG_FILE,
        'maxBytes': 10485760,
        'backupCount': 5
    }


LOGGING['loggers'] = {
    # Disable requests library spam
    'requests': {
        'handlers': HANDLRES,
        'level': 'ERROR',
        'propagate': True,
    },
    '': {
        'handlers': HANDLRES,
        'level': LOG_LEVEL,
        'propagate': True,
    },
    # Slow down module loggings
    'ari.client': {
        'handlers': HANDLRES,
        'level': 'ERROR',
        'propagate': True,
    },
    'swaggerpy.client': {
        'handlers': HANDLRES,
        'level': 'ERROR',
        'propagate': True,
    },
    'Asterisk': {
        'handlers': HANDLRES,
        'level': 'ERROR',
        'propagate': True,
    },
}


try:
    from local_conf import *
except ImportError as e:
    _logger.warning('Did not import local_conf.py.')
