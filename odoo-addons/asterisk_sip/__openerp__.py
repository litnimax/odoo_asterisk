{
    'name': 'Odoo Asterisk SIP Peers Application',
    'summary': '',
    'description': """Manage Asterisk SIP peers.""",
    'version': '1.0',
    'category': 'Telephony',
    'author': 'Communicom',
    'website': 'http://communicom.ru',
    'depends': ['asterisk_base',],
    'installable': True,
    'application': True,
    'auto_install': False,
    'data': [
        'views.xml',
    ],
    'demo': [
    ],
    'js': [],
    'css': [],
    'qweb': [],
}
