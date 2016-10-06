from datetime import datetime, timedelta
import humanize
import logging
from openerp import models, fields, api, _
from openerp import sql_db
import requests
from urlparse import urljoin


logger = logging.getLogger(__name__)



class SipPeer(models.Model):
    _name = 'asterisk.sip_peer'
    _description = 'Asterisk SIP Peer'
    _order = 'write_date desc'

    name = fields.Char(size=80, index=True, required=True)
    note = fields.Char()
    accountcode = fields.Char(size=20)
    amaflags = fields.Char(size=7)
    callgroup = fields.Char(size=7)
    callerid = fields.Char(size=80, string='Caller ID')
    canreinvite = fields.Selection([('yes', 'Yes'), ('no', 'No')],
                                   size=3, string='Can reinvite', default='no')
    context_id = fields.Many2one('asterisk.conf.extensions', ondelete='restrict')
    context = fields.Char(index=True, size=40)
    defaultip = fields.Char(size=15, string='Default IP')
    dtmfmode = fields.Selection(size=10, string='DTMF mode', required=True,
                           default='rfc2833', selection=[('auto', 'Auto'),
                            ('inband', 'Inband'), ('rfc2833', 'RFC2833'),
                            ('info', 'Info'), ('shortinfo', 'Short Info')])
    fromuser = fields.Char(size=80, string='From user')
    fromdomain = fields.Char(size=80, string='From domain')
    host = fields.Char(size=31)
    insecure = fields.Char(size=32)
    language = fields.Char(size=2)
    mailbox = fields.Char(size=50)
    md5secret = fields.Char(size=80)
    nat = fields.Char(selection=[('no', 'No'), ('force_rport', 'Force rport'),
                             ('comedia', 'Comedia'),
                             ('auto_force_rport', 'Auto force rport'),
                             ('auto_comedia', 'Auto comedia'),
                             ('force_rport,comedia', 'Force rport, Comedia')],
                      size=64, default='auto_force_rport')
    permit = fields.Char(size=95)
    deny = fields.Char(size=95)
    mask = fields.Char(size=95)
    pickupgroup = fields.Char(size=10)
    port = fields.Char(size=5, default='')
    qualify = fields.Char(size=5)
    restrictcid = fields.Char(size=1)
    rtptimeout = fields.Char(size=3, string='RTP timeout')
    rtpholdtimeout = fields.Char(size=3, string='RTP hold timeout')
    secret = fields.Char(size=80)
    type = fields.Selection(selection=[('user', 'User'), ('peer', 'Peer'),
                                       ('friend', 'Friend')], required=True,
                                                              default='friend')
    username = fields.Char(size=80, default='', string='User name')
    disallow = fields.Char(size=100, default='all')
    allow = fields.Char(size=100, default='alaw;ulaw,gsm')
    musiconhold = fields.Char(size=100, string='Music on hold')
    regseconds = fields.Char(size=32)
    regseconds_human = fields.Char(compute='_get_regseconds_human',
                                   string='Last Reg')
    ipaddr = fields.Char(size=15, string='IP Address')
    regexten = fields.Char(size=80)
    cancallforward = fields.Char(size=3, default='yes')
    fullcontact = fields.Char(size=80, string='Full contact')
    lastms =fields.Integer()
    useragent = fields.Char(size=20, string='User agent')
    defaultuser = fields.Char(size=80, string='Default user')
    subscribecontext = fields.Char(size=80)
    regserver = fields.Char(size=80)
    callbackextension = fields.Char(size=250)
    peer_type = fields.Selection(selection=[
        ('exten', 'Exten'),
        ('agent', 'Agent'),
        ('provider', 'Provider'),
        ('gateway', 'Gateway'),
    ], index=True)


    _sql_constraints = [
        ('name_uniq', 'UNIQUE(name)', _('Peer name must be unique!'))
    ]


    @api.model
    def grant_asterisk_access(self):
        cr = sql_db.db_connect(self.env.cr.dbname).cursor()
        sql = "GRANT ALL on asterisk_sip_peer to asterisk"
        cr.execute(sql)
        cr.commit()
        cr.close()



    @api.multi
    def prune(self):
        for rec in self:
            logger.debug('Pruning peer {}'.format(self.name))
            try:
                url = self.env['ir.config_parameter'].get_param('barrier_pbx_http_server_url')
                path = '/command'
                r = requests.post(urljoin(url, path),
                                  headers={'Content-Type': 'application/json'},
                                  timeout=5,
                                  data=json.dumps(
                                      {'command': 'sip prune realtime {}'.format(
                                          rec.name)}))
            except Exception as e:
                logger.error('Could not prune sip peer: %s' % e)


    @api.multi
    def _get_regseconds_human(self):
        for rec in self:
            to_translate = self.env.context.get('lang', 'en_US')
            if to_translate != 'en_US':
                humanize.i18n.activate(to_translate)
            rec.regseconds_human = humanize.naturaltime(datetime.fromtimestamp(
                float(rec.regseconds)
            ))



