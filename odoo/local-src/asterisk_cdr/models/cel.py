from odoo import models, fields, api, _
from odoo import sql_db

ASTERISK_ROLE = 'asterisk' # This PostgreSQL role is used to grant access to CEL table

CEL_TYPES = (
    ('CHAN_START', _('Start')),
    ('CHAN_END', _('End')),
    ('ANSWER', _('Answer')),
    ('HANGUP', _('Hangup')),
    ('CONF_ENTER', _('Enter conference')),
    ('CONF_EXIT', _('Exit conference')),
    ('CONF_START', _('Conference start')),
    ('CONF_END', _('Conference end')),
    ('APP_START', _('Application start')),
    ('APP_END', _('Application end')),
    ('PARK_START', _('Park')),
    ('PARK_END', _('Unpark')),
    ('BRIDGE_START', _('Bridge start')),
    ('BRIDGE_END', _('Bridge end')),
    ('BRIDGE_UPDATE', _('Bridge update')),
    ('3WAY_START', _('Three way start')),
    ('3WAY_END', _('Three way end')),
    ('BLINDTRANSFER', _('Blind transfer')),
    ('ATTENDEDTRANSFER', _('Attended transfer')),
    ('TRANSFER', _('Generic transfer')),
    ('PICKUP', _('Pickup')),
    ('FORWARD', _('Forward')),
    ('HOOKFLASH', _('Hookflash')),
    ('LINKEDID_END', _('Linkedid end')),
    ('USER_DEFINED', _('User defined')),
)

class Cel(models.Model):
    _name = 'asterisk.cel'
    _description = 'Asterisk CEL'
    _rec_name = 'eventtype'

    eventtype = fields.Selection(size=30, string='Event type',
        selection=CEL_TYPES,
        help='The name of the event',index=True)
    eventtime = fields.Datetime(string='Time', index=True)
    userdeftype = fields.Char(size=255, string='User event type', index=True)
    cid_name = fields.Char(size=80, string='CID name', index=True)
    cid_num = fields.Char(size=80, string='CID number', index=True)
    cid_ani = fields.Char(size=80, string='CID ANI', index=True)
    cid_rdnis = fields.Char(size=80, string='CID RDNIS', index=True)
    cid_dnid = fields.Char(size=80, string='CID DNID', index=True)
    exten = fields.Char(size=80, string='Extension',
        help='The extension in the dialplan', index=True)
    context = fields.Char(size=80, string='Context')
    channame = fields.Char(size=80, string='Channel', index=True,
        help='The name assigned to the channel in which the event took place')
    appname = fields.Char(size=80, string='Application')
    appdata = fields.Char(size=80, string='Application data')
    amaflags = fields.Integer(string='AMA flags')
    accountcode = fields.Char(size=20, string='Account', index=True)
    peeraccount = fields.Char(size=20, string='Peer account', index=True)
    uniqueid = fields.Char(size=150, string='Uniqueid', index=True)
    linkedid = fields.Char(size=150, string='Linked ID', index=True)
    userfield = fields.Char(size=255, string='User field', index=True)
    peer = fields.Char(size=80, string='Other channel', index=True)
    cdr = fields.Many2one('asterisk.cdr', ondelete='cascade')
