import json
from odoo import api, fields, models, _


class AsteriskBaseSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    _name = 'asterisk.settings'

    PARAMS = ['sub_addr', 'pub_addr', 'agent_repository_ssh_url',
              'agent_repository_public_key', 'agent_repository_private_key',
              'ssh_authorized_keys', 'no_asterisk']

    sub_addr = fields.Char(string='SUB address')
    pub_addr = fields.Char(string='PUB address')
    agent_repository_ssh_url = fields.Char(string="Repository SSH URL")
    agent_repository_public_key = fields.Text()
    agent_repository_private_key = fields.Text()
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


    def notify_agents(self):
        self.ensure_one()
        dict_params = {}
        for param in self.PARAMS:
            result_list = [k for k in param]
            result_list[0] = result_list[0].capitalize()
            try:
                while True:
                    pos = result_list.index('_')
                    result_list[pos+1] = result_list[pos+1].capitalize()
                    result_list.pop(pos)
            except ValueError:
                dict_params[''.join(result_list)] = eval('self.{}'.format(param))
        msg = {
            'Message': 'UpdateSettings',
            'To': '*',
        }
        msg.update(dict_params)
        z_tell(self, msg)
