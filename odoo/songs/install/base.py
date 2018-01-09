# -*- coding: utf-8 -*-
# Copyright 2016 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from base64 import b64encode
from pkg_resources import Requirement, resource_string
from anthem.lyrics.records import create_or_update


def setup_company(ctx, req):
    """ Setup company """
    company = ctx.env.ref('base.main_company')
    company.name = 'Asterisk company'

    # load logo on company
    logo_content = resource_string(req, 'data/images/logo.png')
    logo = b64encode(logo_content)
    company.logo = logo

    values = {
        'name': "Asterisk company Address",
        'street': "Asterisk Street 1",
        'zip': "1000",
        'city': "Chisington",
        'parent_id': company.id,
        'logo': logo,
        'currency_id': ctx.env.ref('base.CHF').id
    }
    create_or_update(ctx, 'res.company', '__setup__.company_asterisk', values)


def setup_language(ctx):
    """ install language and configure locale formatting """
    for code in ('ru_RU',):
        ctx.env['base.language.install'].create({'lang': code}).lang_install()
    ctx.env['res.lang'].search([]).write({
        'grouping': [3, 0],
        'date_format': '%d/%m/%Y',
    })


def main(ctx):
    """ Create demo data """
    req = Requirement.parse('odoo-asterisk')
    setup_language(ctx)
    setup_company(ctx, req)
