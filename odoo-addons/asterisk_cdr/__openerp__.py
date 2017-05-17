{
    'name': 'Odoo Asterisk Call Detail Records',
    'summary': '',
    'description': """View CDR statistics.""",
    'version': '1.0',
    'category': 'Telephony',
    'author': 'Communicom',
    'website': 'http://communicom.ru',
    'depends': ['asterisk_base', 'board'],
    'installable': True,
    'application': True,
    'auto_install': False,
    'data': [
        'views/cel.xml',
        'views/cdr.xml',
    ],
    'demo': [
    ],
    'js': [],
    'css': [],
    'qweb': [],
}
