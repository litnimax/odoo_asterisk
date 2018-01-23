import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError, Warning, ValidationError

_logger = logging.getLogger(__name__)

class AsteriskConf(models.Model):
    _name = 'asterisk.conf'
    _description = 'Configuration Files'
    _rec_name = 'name'
    _order = 'name'

    name = fields.Char(required=True)
    server = fields.Many2one(comodel_name='asterisk.server', required=True)
    content = fields.Text()
    sync_date = fields.Datetime(readonly=True)
    sync_uid = fields.Many2one('res.users', readonly=True, string='Sync by')



    _sql_constraints = [
        ('name_server_idx', 'unique(name,server)',
            _('This file already exists on this server.')),
    ]


    def upload_conf(self):
        self.ensure_one()
        self.server.upload_conf(self)
        #self.server.asterisk_reload()
        # Update last sync
        self.sync_date = fields.Datetime.now()
        self.sync_uid = self.env.uid
