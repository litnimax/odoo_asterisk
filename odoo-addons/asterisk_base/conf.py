from openerp import models, fields, api, _


class Conf(models.Model):
    _name = 'asterisk.conf'
    _description = 'Configuration Files'
    _recname = 'filename'

    filename = fields.Char(required=True)
    content = fields.Text()
