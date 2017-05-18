import logging
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


class Channel(models.Model):
    _name = 'asterisk.channel'
    _rec_name = 'channel'

    channel = fields.Char(index=True)
    uniqueid = fields.Char(size=150, string='Uniqueid', index=True)

    """
{u'Context': u'extensions', u'ConnectedLineNum': u'<unknown>',
 u'Func': u'channel_snapshot_update', u'SequenceNumber': u'971',
 u'AccountCode': '', u'ChannelState': u'0', u'Timestamp': u'1495105534.669549',
 u'Exten': u'200', u'CallerIDNum': u'test1', u'Uniqueid': u'ubuntu-1495105534.144',
 u'Priority': u'1', u'ConnectedLineName': u'<unknown>',
 u'SystemName': u'ubuntu', u'File': u'manager_channels.c',
  u'CallerIDName': u'<unknown>',
  u'Privilege': u'call,all', u'Line': u'650', u'Event': u'Newchannel',
  u'Channel': <Asterisk.Manager.BaseChannel referencing channel u'SIP/test1-00000015' o
  f <Asterisk.Manager.Manager connected as asterisk_admin to 192.168.56.102:5038>>,
   u'ChannelStateDesc': u'Down'}
    """

    @api.model
    def new_channel(self, values):
        self.create({
            'channel': values.get('Channel'),
            'uniqueid': values.get('Uniqueid')
        })
        return True


    @api.model
    def hangup_channel(self, values):
        uniqueid = values.get('Uniqueid')
        channel = values.get('Channel')
        found = self.search([('uniqueid', '=', uniqueid)])
        if found:
            _logger.debug('Found channel {}'.format(channel))
            found.unlink()
        else:
            _logger.warning('Channel {} not found for hangup.'.format(uniqueid))
