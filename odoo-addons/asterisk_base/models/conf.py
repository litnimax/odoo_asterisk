import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError, Warning, ValidationError

_logger = logging.getLogger(__name__)

class AsteriskConf(models.Model):
    _name = 'asterisk.conf'
    _description = 'Configuration Files'
    _rec_name = 'filename'
    _order = 'filename'

    filename = fields.Char(required=True)
    server = fields.Many2one(comodel_name='asterisk.server',
        required=True)
    content = fields.Text()
    sync_date = fields.Datetime(readonly=True)
    sync_uid = fields.Many2one('res.users', readonly=True, string='Sync by')



    _sql_constraints = [
        ('filename_server_idx', 'unique(filename,server)',
            _('This file already exists on this server.')),
    ]


    def sync_conf(self):
        self.ensure_one()
        session = self.server.get_ajam_session()
        self.server.sync_conf(self, session)
        self.server.asterisk_reload()
        # Update last sync
        self.sync_date = fields.Datetime.now()
        self.sync_uid = self.env.uid
