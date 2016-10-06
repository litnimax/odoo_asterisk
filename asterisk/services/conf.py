import logging

STASIS_APP = 'barrier2'

ODOO_HOST = 'localhost'
ODOO_PORT = 8069
ODOO_DB = 'barrier3'
ODOO_USER = 'pbx_broker'
ODOO_PASSWORD = '123'
ODOO_CONNECTION_TIMEOUT = 15
ODOO_RECONNECT_TIMEOUT = 1

ARI_RECONNECT_TIMEOUT = 1


PICTURE_SAVE_TIMEOUT = 15

LOG_CONSOLE = True
LOG_FILE = './stasis.log'
LOG_LEVEL = logging.DEBUG

try:
    from local_conf import *
except ImportError:
    pass


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
            'backupCount': 5
        }
    },
    'loggers': {
        'requests': {
            'handlers': ['file', 'console'],
            'level': 'ERROR',
            'propagate': False,
        },
        'common': {
            'handlers': ['console', 'file'] if LOG_CONSOLE else ['file'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
        'ari.client': {
            'handlers': ['console', 'file'] if LOG_CONSOLE else ['file'],
            'level': logging.ERROR,
            'propagate': False,
        },
    }
}
