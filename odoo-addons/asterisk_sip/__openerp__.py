{
    'name': 'Odoo Asterisk SIP Peer Management Application',
    'summary': '',
    'description': """Manage Asterisk SIP peers.""",
    'version': '1.0',
    'category': 'Telephony',
    'author': 'Communicom',
    'website': 'http://communicom.ru',
    'depends': ['asterisk_base', 'asterisk_cdr'],
    'installable': True,
    'application': True,
    'auto_install': False,
    'data': [
        'views/peer_status.xml',
        'views/common_views.xml',
        'views/user.xml',
        'views/trunk.xml',
        'views/res_users.xml',
        'views/res_partner.xml',
        'views/resources.xml',
    ],
    'qweb': [
        'static/src/xml/*.xml'
    ],
}
