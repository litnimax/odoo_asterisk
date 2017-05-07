from odoo import api, fields, models, _


class AsteriskBaseSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    _name = 'asterisk.settings'

    no_asterisk = fields.Boolean(string='No Asterisk')

    @api.multi
    def set_params(self):
        self.ensure_one()
        self.env['ir.config_parameter'].set_param('asterisk_base.no_asterisk',
                                                  self.no_asterisk)



    def get_default_params(self, fields):
        res = {}
        res['no_asterisk'] = self.env['ir.config_parameter'].get_param(
                                        'asterisk_base.no_asterisk', '').strip()
        return res
