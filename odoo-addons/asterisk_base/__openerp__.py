{
    'name': 'Odoo Asterisk Management Base Application',
    'summary': '',
    'description': """Use Odoo to Manage your Asterisk.""",
    'version': '1.0',
    'category': 'Telephony',
    'author': 'Communicom',
    'website': 'http://communicom.ru',
    'depends': ['web'],
    'installable': True,
    'application': True,
    'auto_install': False,
    'data': [
        'views/views.xml',
        'views/templates.xml',
        'views/conf.xml',
        'views/server.xml',
        'views/settings.xml',
        # Data files
        'data/server.xml',
        'data/features_conf.xml',
        'data/http_conf.xml',
        'data/manager_conf.xml',
    ],
    'demo': [
    ],
    'qweb': [
        'static/src/xml/*.xml',
    ],
}
