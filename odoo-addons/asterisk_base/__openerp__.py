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
        'templates.xml',
        'views.xml',
        'data/features_conf.xml',
    ],
    'demo': [
    ],
    'qweb': [
        'static/src/xml/*.xml',
    ],
}
