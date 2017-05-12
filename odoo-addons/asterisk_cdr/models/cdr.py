from datetime import datetime, timedelta
import humanize
import logging
from odoo import models, fields, api, _
from odoo import sql_db
import requests
from urlparse import urljoin

_logger = logging.getLogger(__name__)

ASTERISK_ROLE = 'asterisk' # This PostgreSQL role is used to grant access to CDR table

DISPOSITION_TYPES = (
    ('NO ANSWER', 'No answer'),
    ('FAILED', 'Failed'),
    ('BUSY', 'Busy'),
    ('ANSWERED', 'Answered'),
    ('CONGESTION', 'Congestion'),
)


class Cdr(models.Model):
    _name = 'asterisk.cdr'
    _description = 'Call Detail Record'
    _order = 'started desc'
    _rec_name = 'uniqueid'

    accountcode = fields.Char(size=20, string='Account code', index=True)
    src = fields.Char(size=80, string='Src', index=True)
    dst = fields.Char(size=80, string='Dst', index=True)
    dcontext = fields.Char(size=80, string='Dcontext')
    clid = fields.Char(size=80, string='Clid', index=True)
    channel = fields.Char(size=80, string='Channel', index=True)
    dstchannel = fields.Char(size=80, string='Dst channel', index=True)
    lastapp = fields.Char(size=80, string='Last app')
    lastdata = fields.Char(size=80, string='Last data')
    started = fields.Datetime(index=True, oldname='start')
    answered = fields.Datetime(index=True, oldname='answer')
    ended = fields.Datetime(index=True, oldname='end')
    duration = fields.Integer(string='Duration', index=True)
    billsec = fields.Integer(string='Billsec', index=True)
    disposition = fields.Char(size=45, string='Disposition', index=True)
    amaflags = fields.Integer(string='AMA flags')
    userfield = fields.Char(size=255, string='Userfield')
    uniqueid = fields.Char(size=150, string='Uniqueid', index=True)
    peeraccount = fields.Char(size=20, string='Peer account', index=True)
    linkedid = fields.Char(size=150, string='Linked id')
    sequence = fields.Integer(string='Sequence')
    recording_filename = fields.Char()
    recording_data = fields.Binary()
    recording_widget = fields.Char(compute='_get_recording_widget')
    # QoS
    ssrc = fields.Char(string='Our SSRC')
    themssrc = fields.Char(string='Other SSRC')
    lp = fields.Integer(string='Local Lost Packets')
    rlp = fields.Integer(string='Remote Lost Packets')
    rxjitter = fields.Float(string='RX Jitter')
    txjitter = fields.Float(string='TX Jitter')
    rxcount = fields.Integer(string='RX Count')
    txcount = fields.Integer(string='TX Count')
    rtt = fields.Float(string='Round Trip Time')
    # CEL related fields
    cel_count = fields.Integer(compute='_get_cel_count')
    cels = fields.One2many(comodel_name='asterisk.cel',
                           inverse_name='cdr')


    def __init__(self, pool, cr):
        init_res = super(Cdr, self).__init__(pool, cr)
        cr.execute("""CREATE OR REPLACE FUNCTION update_cel_cdr_field() RETURNS trigger AS $$
            BEGIN
            UPDATE asterisk_cel set cdr = NEW.id
                WHERE asterisk_cel.uniqueid = NEW.uniqueid;
            RETURN NULL;
            END; $$ LANGUAGE 'plpgsql';

            DROP TRIGGER IF EXISTS update_cel_cdr_field  on asterisk_cdr;
            CREATE TRIGGER update_cel_cdr_field AFTER INSERT on asterisk_cdr
                FOR EACH ROW EXECUTE PROCEDURE update_cel_cdr_field();
            """)
        return init_res


    """
    LOL :-) Asterisk does not use Odoo to store CDRs :-))
    def create(self, vals):
        res = super(Cdr, self).create(vals)
        found = self.env['asterisk.cel'].search([('uniqueid', '=', res.uniqueid)])
        if found:
            _logger.debug('Updating {} CELs for {}'.format(
                len(found), res.uniqueid))
            found.write({'cdr': res.id})
    """


    @api.multi
    def _get_cel_count(self):
        for rec in self:
            rec.cel_count = self.env['asterisk.cel'].search_count([
                ('cdr', '=', rec.id)])


    @api.model
    def grant_asterisk_access(self):
        cr = sql_db.db_connect(self.env.cr.dbname).cursor()
        sql = "GRANT ALL on asterisk_cdr to %s" % ASTERISK_ROLE
        cr.execute(sql)
        sql = "GRANT ALL on asterisk_cdr_id_seq to %s" % ASTERISK_ROLE
        cr.execute(sql)
        cr.commit()
        cr.close()


    @api.multi
    def _get_recording_widget(self):
        for rec in self:
            rec.recording_widget = '<audio id="sound_file" preload="auto" ' \
                    'controls="controls"> ' \
                    '<source src="/web/content?model=asterisk.cdr&' \
                    'id={}&filename={}.wav&field=recording_data" ' \
                    'type="audio/wav"/>'.format(rec.id, rec.recording_filename)


    @api.model
    def log_qos(self, values):
        _logger.debug(values)
        uniqueid = values.get('uniqueid')
        linkedid = values.get('linkedid')
        cdrs = self.env['asterisk.cdr'].search([
            ('uniqueid', '=', uniqueid),
            ('linkedid', '=', linkedid),
            ('end', '>', (datetime.now() - timedelta(seconds=10)).strftime(
                '%Y-%m-%d %H:%M:%S')
            ),
        ])
        if not cdrs:
            _logger.warning('Omitting QoS, CDR not found!')
            return False
        else:
            _logger.debug('Found CDR for QoS.')
            cdr = cdrs[0]
            cdr.ssrc =values.get('ssrc')
            cdr.themssrc = values.get('themssrc')
            cdr.lp = int(values.get('lp'))
            cdr.rlp = int(values.get('rlp'))
            cdr.rxjitter = float(values.get('rxjitter'))
            cdr.txjitter = float(values.get('txjitter'))
            cdr.rxcount = int(values.get('rxcount'))
            cdr.txcount = int(values.get('txcount'))
            cdr.rtt = float(values.get('rtt'))
            return True


    @api.model
    def save_call_recording(self, call_id, file_data):
        _logger.debug('save_call_recording for callid {}.'.format(call_id))
        rec = self.env['asterisk.cdr'].search([('uniqueid', '=', call_id),])
        if not rec:
            _logger.warning(
                'save_call_recording - cdr not found by id {}.'.format(call_id))
            return False
        else:
            _logger.debug('Found CDR for id {}.'.format(call_id))
            rec.recording_filename = '{}.wav'.format(call_id)
            rec.recording_data = file_data
            return True
