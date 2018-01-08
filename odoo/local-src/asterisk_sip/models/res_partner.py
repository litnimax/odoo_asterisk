from odoo import models, fields, api
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _inherit = 'res.partner'


    @api.model
    def originate_call(self, number, context={}):
        user = self.env['res.users'].browse([self.env.uid])[0]
        if user.sip_peer:
            user.sip_peer.server.originate_call(
                user.sip_peer, number)
        else:
            raise UserError('You don\'t have a SIP peer to make a call!')
