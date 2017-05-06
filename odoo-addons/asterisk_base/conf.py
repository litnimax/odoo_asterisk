from openerp import models, fields, api, _


class Conf(models.Model):
    _name = 'asterisk.conf'
    _description = 'Configuration Files'
    _recname = 'filename'

    filename = fields.Char(required=True)
    # Trick to show filename above content when creating new file
    filename_on_create = fields.Char()
    content = fields.Text()


    @api.onchange("filename_on_create")
    def _onchange_filename_on_create(self):
        self.filename = self.filename_on_create
