from collections import defaultdict
import json
import logging
import requests
from xml.etree import cElementTree as ET
from odoo import api, models, fields, _
from odoo.exceptions import UserError, Warning, ValidationError
from pyajam import Pyajam
import paho.mqtt.publish as publish


_logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 6


def etree_to_dict(t):
    """
    Helper function to parse Asterisk mxml responses over AJAM.
    """
    d = {t.tag: {} if t.attrib else None}
    children = list(t)
    if children:
        dd = defaultdict(list)
        for dc in map(etree_to_dict, children):
            for k, v in dc.items():
                dd[k].append(v)
        d = {t.tag: {k:v[0] if len(v) == 1 else v for k, v in dd.items()}}
    if t.attrib:
        d[t.tag].update(('@' + k, v) for k, v in t.attrib.items())
    if t.text:
        text = t.text.strip()
        if children or t.attrib:
            if text:
              d[t.tag]['#text'] = text
        else:
            d[t.tag] = text
    return d



class AsteriskServer(models.Model):
    _name = 'asterisk.server'

    name = fields.Char(required=True)
    uid = fields.Char(string='UID', unique=True)
    host = fields.Char()
    note = fields.Text()
    ami_username = fields.Char(string='AMI username')
    ami_password = fields.Char(string='AMI password')
    ami_port = fields.Integer(default=5038, string='AMI port')
    http_port = fields.Integer(default=8088, string='HTTP port')
    https_port = fields.Integer(default=8089, string='HTTPS port')
    use_https = fields.Boolean(string='Use HTTPS')
    certificate = fields.Text(string='TLS certificate')
    key = fields.Text(string='TLS private key')
    conf_files = fields.One2many(comodel_name='asterisk.conf',
                                 inverse_name='server')
    sync_date = fields.Datetime(readonly=True)
    sync_uid = fields.Many2one('res.users', readonly=True, string='Sync by')
    cli_url = fields.Char(string='Asterisk CLI URL',
                          default='ws://localhost:8010/websocket')
    cli_area = fields.Text(compute='_get_cli_area', inverse='_set_cli_area')

    _sql_constraints = [
        ('uid_unique', 'UNIQUE(uid)', 'This UID is already used.'),
    ]

    @api.multi
    def _get_cli_area(self):
        """
        We use cli_url to set CLI URL and reflect this in cli_area to take it from JS.
        """
        for rec in self:
            rec.cli_area = rec.cli_url


    @api.multi
    def _set_cli_area(self):
        """
        STUB as I don't know yet how to extend WEB widgets and get rid of this shit.
        """
        pass


    def no_asterisk_mode(self):
        # Check Asterisk fake mode
        return self.env['ir.config_parameter'].get_param(
            'asterisk_base.no_asterisk', False)


    def asterisk_command(self, command):
        self.ensure_one()
        if self.no_asterisk_mode():
            return
        ajam = Pyajam(server=self.host,
                    username=self.ami_username,
                    password=self.ami_password,
                    port=self.http_port,
                    path='') # Do not set prefix
        if not ajam.login():
            raise UserError('Asterisk AMI login error!')
        response = ajam.command(command)


    def upload_conf(self, conf):
        broker_host = self.env['ir.config_parameter'].get_param(
            'asterisk.mqtt_server', 'nonresolvable.hz')
        _logger.debug('Uploading {} @ {} via {}...'.format(
            conf.name,
            conf.server.name,
            broker_host))
        topic = 'asterisk/' + self.uid + '/file'
        msg = {
            'Content': conf.content,
            'Name': conf.name,
            'DestinationFolder': '/etc/asterisk',
        }
        publish.single(topic, json.dumps(msg), hostname=broker_host)


    def upload_all_conf(self):
        self.ensure_one()
        if self.no_asterisk_mode():
            _logger.warning('No Asterisk mode enabled, not doing anything.')
            return
        # Start sending config files to the server
        for conf in self.conf_files:
            self.upload_conf(conf)
        # Update last sync
        self.sync_date = fields.Datetime.now()
        self.sync_uid = self.env.uid


    def download_all_conf(self, conf):
        broker_host = self.env['ir.config_parameter'].get_param(
            'asterisk.mqtt_server', 'nonresolvable.hz')
        _logger.debug('Sending download request for all files.')
        topic = 'asterisk/' + self.uid + '/upload_asterisk_configs'
        publish.single(topic, '', hostname=broker_host)


    @api.multi
    def originate_call(self, sip_peer, number):
        self.ensure_one()
        _logger.debug('Originate call to {} for {}.'.format(number, sip_peer))
        self.env['bus.bus'].sendone(
            'stasis_apps',
            json.dumps({
                'command': 'originate',
                'server_id': self.id,
                'endpoint': 'SIP/' + sip_peer.name,
                'exten': number,
                'callerid': sip_peer.callerid,
                'context': 'users',
                'user_id': self.env.user.id,
            })
        )
