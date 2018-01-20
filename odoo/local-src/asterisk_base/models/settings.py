import json
from odoo import api, fields, models, _


class AsteriskBaseSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    _name = 'asterisk.settings'

    PARAMS = ['mqtt_server', 'ssh_authorized_keys', 'no_asterisk']

    mqtt_server = fields.Char(string='MQTT Broker server')
    ssh_authorized_keys = fields.Text(string='SSH Authorized Keys',
        help='These keys file is distriubuted as is to agent\'s homedir ~/.ssh')
    no_asterisk = fields.Boolean(string='No Asterisk',
        help='When this is set all communication with Asterisk is considered successful.\n'
             'This can be used to test the management interface without errors when '
             'there is not Asterisk server connected.')



    @api.multi
    def set_params(self):
        self.ensure_one()
        for field_name in self.PARAMS:
            value = getattr(self, field_name, '')
            self.env['ir.config_parameter'].set_param(
                'asterisk.' + field_name, value)


    def get_default_params(self, fields):
        res = {}
        for field_name in self.PARAMS:
            res[field_name] = self.env[
                'ir.config_parameter'].get_param(
                    'asterisk.' + field_name, '')
        return res
