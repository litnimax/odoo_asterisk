from openerp import models, fields, api, _


class Conf(models.Model):
    _name = 'asterisk.conf'
    _description = 'Configuration Files'
    _rec_name = 'filename'

    filename = fields.Char(required=True)
    # Trick to show filename above content when creating new file
    filename_on_create = fields.Char()
    content = fields.Text()

    _sql_constraints = [
        ('filename', 'unique(filename)', _('This file already exists.'))
    ]

    @api.onchange('filename_on_create', 'filename')
    def _onchange_filename_on_create(self):
        """
        This is used to show filename on the same tab on create. Information tab
        is invisible.
        """
        if not self.write_date:
            self.filename = self.filename_on_create
        else:
            self.filename_on_create = self.filename
