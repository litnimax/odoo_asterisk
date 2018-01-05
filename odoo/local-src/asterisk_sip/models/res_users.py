from odoo import models, fields


class ResUsers(models.Model):
    _inherit = "res.users"

    sip_peer = fields.Many2one(comodel_name='asterisk.sip_peer',
                               string='SIP peer')
