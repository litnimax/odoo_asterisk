{
    'name': "Odoo PBX",
    'version': '1.0',
    'depends': ['web'],
    'author': "Communicom",
    'category': 'Telephony',
    'description': """
    Odoo PBX for company.
    """,
    # data files always loaded at installation
    'data': [
        'views/views.xml',
        'views/cdr.xml',
    ],
    # data files containing optionally loaded demonstration data
    'demo': [

    ],
}
