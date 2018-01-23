from datetime import datetime, timedelta
import logging
import random
import string
import humanize
import requests
from urlparse import urljoin
from openerp import models, fields, api, _
from openerp import sql_db


logger = logging.getLogger(__name__)

DEFAULT_SECRET_LENGTH = 10
PEER_TYPES = [
    ('user', 'User'),
    ('trunk', 'Trunk'),
]


def _generate_secret(length=DEFAULT_SECRET_LENGTH):
    chars = string.letters + string.digits
    password = ''
    while True:
        password = ''.join(map(lambda x: random.choice(chars), range(length)))
        if filter(lambda c: c.isdigit(), password) and \
                filter(lambda c: c.isalpha(), password):
            break
    return password



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
    #context_id = fields.Many2one('asterisk.conf.extensions', ondelete='restrict')
    context = fields.Char(index=True, size=40)
    defaultip = fields.Char(size=15, string='Default IP')
    dtmfmode = fields.Selection(size=10, string='DTMF mode', required=True,
                           default='rfc2833', selection=[('auto', 'Auto'),
                            ('inband', 'Inband'), ('rfc2833', 'RFC2833'),
                            ('info', 'Info'), ('shortinfo', 'Short Info')])
    fromuser = fields.Char(size=80, string='From user')
    fromdomain = fields.Char(size=80, string='From domain')
    host = fields.Char(size=31, default='dynamic')
    outboundproxy = fields.Char(size=80)
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
    secret = fields.Char(size=80, default=lambda x: _generate_secret())
    type = fields.Selection(selection=[('user', 'User'), ('peer', 'Peer'),
                                       ('friend', 'Friend')], required=True,
                                                              default='friend')
    username = fields.Char(size=80, string='User name')
    disallow = fields.Char(size=100)
    allow = fields.Char(size=100, default='all')
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
    peer_type = fields.Selection(selection=PEER_TYPES, index=True)
    server = fields.Many2one(comodel_name='asterisk.server', required=True)
    peer_statuses = fields.One2many(comodel_name='asterisk.sip_peer_status',
                                    inverse_name='peer')
    peer_status_count = fields.Integer(compute='_get_peer_status_count',
                                       store=True, string='Events')



    _sql_constraints = [
        ('name_uniq', 'UNIQUE(name)', _('Peer name must be unique!'))
    ]


    @api.depends('peer_statuses')
    def _get_peer_status_count(self):
        for rec in self:
            rec.peer_status_count = self.env[
                'asterisk.sip_peer_status'].search_count([
                    ('peer', '=', rec.id)])



    @api.multi
    def generate_sip_peers(self):
        self.ensure_one()
        found_include = False
        sip_auto_conf = self.env['asterisk.conf'].search(['&',
            ('name', '=', 'sip_auto_peers.conf'),
            ('server', '=', self.server.id)])
        if not sip_auto_conf:
            sip_auto_conf = self.env['asterisk.conf'].create({
                'server': self.server.id,
                'name': 'sip_auto_peers.conf',
            })
        # Now let see if sip.conf includes sip_auto_peers
        sip_conf = self.env['asterisk.conf'].search(['&',
            ('server', '=', self.server.id),
            ('name', '=', 'sip.conf')])
        for line in sip_conf.content.split('\n'):
            if line.find('#tryinclude sip_auto_peers.conf') != -1:
                found_include = True
                break
        if not found_include:
            sip_conf.content += '\n\n#tryinclude sip_auto_peers.conf\n'

        peers = []
        content = u''
        # Now do some sorting. We want extensins first, then agents, providers and gws.
        peer_type_order = ['user', 'trunk']
        for pto in peer_type_order:
            found_peers = self.env['asterisk.sip_peer'].search(
                [('peer_type', '=', pto)], order='name')
            for p in found_peers:
                peers.append(p)
        # Now let proceed peer fields
        for peer in peers:
            fields =  peer.fields_get_keys()
            # Cleanup fields list to have only Asterisk options
            fields_to_remove = ['create_date', 'create_uid', 'display_name',
                                '__last_update', 'id', 'peer_type', 'server',
                                'regseconds_human', 'peer_statuses', 'peer_status_count',
                                'write_uid', 'write_date', 'note', 'name']
            # Sort!
            fields.sort()
            for f in fields_to_remove:
                fields.remove(f)
            # Create section
            content += u'[{}] ;{}\n'.format(peer.name, peer.note) if peer.note \
                else u'[{}]\n'.format(peer.name)
            gen = [f for f in fields if getattr(peer, f) != False]
            for f in gen:
                content += u'{} = {}\n'.format(f, getattr(peer, f))
            content += '\n'
        # Save config
        sip_auto_conf.content = content
        if found_include:
            sip_auto_conf.upload_conf()
        else:
            sip_auto_conf.server.upload_all_conf()


    @api.multi
    def _get_regseconds_human(self):
        for rec in self:
            to_translate = self.env.context.get('lang', 'en_US')
            if to_translate != 'en_US':
                humanize.i18n.activate(to_translate)
            rec.regseconds_human = humanize.naturaltime(datetime.fromtimestamp(
                float(rec.regseconds)
            ))


    @api.multi
    def sync(self):
        self.ensure_one()
        self.generate_sip_peers()
