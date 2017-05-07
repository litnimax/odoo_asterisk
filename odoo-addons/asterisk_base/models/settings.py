from odoo import api, fields, models, _


class AsteriskBaseSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    _name = 'asterisk.settings'

    no_asterisk = fields.Boolean(string='No Asterisk',
        help='When this is set all communication with Asterisk is considered successful.\n'
             'This can be used to test the management interface without errors when '
             'there is not Asterisk server connected.')

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
