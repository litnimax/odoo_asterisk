from odoo import models, fields, api, _
from odoo import sql_db

ASTERISK_ROLE = 'asterisk' # This PostgreSQL role is used to grant access to CEL table

CEL_TYPES = (
    ('CHAN_START', _('Channel started')),
    ('CHAN_END', _('The time a channel was terminated')),
    ('ANSWER', _('The time a channel was answered (ie, phone taken off-hook)')),
    ('HANGUP', _('The time at which a hangup occurred')),
    ('CONF_ENTER', _('The time a channel was connected into a conference room')),
    ('CONF_EXIT', _('The time a channel was removed from a conference room')),
    ('CONF_START', _('The time the first person enters a conference room')),
    ('CONF_END', _('The time the last person left a conference room')),
    ('APP_START', _('The time a tracked application was started')),
    ('APP_END', _('The time a tracked application ended')),
    ('PARK_START', _('The time a call was parked')),
    ('PARK_END', _('Unpark event')),
    ('BRIDGE_START', _('The time a bridge is started')),
    ('BRIDGE_END', _('The time a bridge is ended')),
    ('BRIDGE_UPDATE', _('This is a replacement channel (Masquerade)')),
    ('3WAY_START', _('When a 3-way conference starts (usually via attended transfer)')),
    ('3WAY_END', _('When one or all exit a 3-way conference')),
    ('BLINDTRANSFER', _('When a blind transfer is initiated')),
    ('ATTENDEDTRANSFER', _('When an attended transfer is initiated')),
    ('TRANSFER', _('Generic transfer initiated; not used yet...?')),
    ('PICKUP', _('This channel picked up the peer channel')),
    ('FORWARD', _('This channel is being forwarded somewhere else')),
    ('HOOKFLASH', _('So far, when a hookflash event occurs on a DAHDI interface')),
    ('LINKEDID_END', _('The last channel with the given linkedid is retired')),
    ('USER_DEFINED', _('Triggered from the dialplan, and has a name given by the user')),
)

class Cel(models.Model):
    _name = 'asterisk.cel'
    _description = 'Asterisk CEL'
    _rec_name = 'eventtype'

    eventtype = fields.Selection(size=30, string='Event type',
        selection=CEL_TYPES,
        help='The name of the event',index=True)
    eventtime = fields.Datetime(string='Event time', index=True)
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


    @api.model
    def grant_asterisk_access(self):
        cr = sql_db.db_connect(self.env.cr.dbname).cursor()
        sql = "GRANT ALL on asterisk_cel to %s" % ASTERISK_ROLE
        cr.execute(sql)
        sql = "GRANT ALL on asterisk_cel_id_seq to %s" % ASTERISK_ROLE
        cr.execute(sql)
        cr.commit()
        cr.close()
