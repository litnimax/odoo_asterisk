import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError, Warning, ValidationError

_logger = logging.getLogger(__name__)

class AsteriskConf(models.Model):
    _name = 'asterisk.conf'
    _description = 'Configuration Files'
    _rec_name = 'filename'

    filename = fields.Char(required=True)
    server = fields.Many2one(comodel_name='asterisk.server',
        required=True)
    content = fields.Text()
    # Trick to show filename above content when creating new file
    filename_on_create = fields.Char()
    server_on_create = fields.Many2one(comodel_name='asterisk.server',
        string='Server')


    _sql_constraints = [
        ('filename', 'unique(filename)', _('This file already exists.'))
    ]


    @api.onchange('filename_on_create', 'filename', 'server', 'server_on_create')
    def _onchange_on_create(self):
        """
        This is used to show filename on the same tab on create. Information tab
        is invisible.
        """
        if not self.write_date:
            self.filename = self.filename_on_create
            self.server = self.server_on_create
        else:
            self.filename_on_create = self.filename
            self.server_on_create = self.server
