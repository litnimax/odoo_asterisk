import logging
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


class Channel(models.Model):
    _name = 'asterisk.channel'
    _rec_name = 'channel'

    channel = fields.Char(index=True)
    uniqueid = fields.Char(size=150, index=True)
    linkedid = fields.Char(size=150, index=True)
    context = fields.Char(size=80)
    connected_line_num = fields.Char(size=80)
    connected_line_name = fields.Char(size=80)
    state = fields.Char(size=80)
    state_desc = fields.Char(size=256, string="State Description")
    exten = fields.Char(size=32)
    callerid_num = fields.Char(size=32)
    callerid_name = fields.Char(size=32)
    system_name = fields.Char(size=32)
    accountcode = fields.Char(size=80)
    priority = fields.Char(size=4)
    timestamp = fields.Char(size=20)
    app = fields.Char(size=32, string='Application')
    app_data = fields.Char(size=512, string='Application Data')


    @api.model
    def new_channel(self, values):
        self.env['asterisk.channel'].create({
            'channel': values.get('Channel'),
            'uniqueid': values.get('Uniqueid'),
            'context': values.get('Context'),
            'connected_line_num': values.get('ConnectedLineNum'),
            'connected_line_name': values.get('ConnectedLineName'),
            'state': values.get('ChannelState'),
            'state_desc': values.get('ChannelStateDesc'),
            'exten': values.get('Exten'),
            'callerid_num': values.get('CallerIDNum'),
            'callerid_name': values.get('CallerIDName'),
            'accountcode': values.get('AccountCode'),
            'priority': values.get('Priority'),
            'timestamp': values.get('Timestamp'),
            'system_name': values.get('SystemName'),
        })
        self.env['bus.bus'].sendone('asterisk_channels', 'message');
        return True


    @api.model
    def update_channel_state(self, values):
        channel = self.env['asterisk.channel'].search([
            ('uniqueid', '=', values.get('Uniqueid'))])
        if channel:
            channel.write({
                'channel': values.get('Channel'),
                'linkedid': values.get('Linkedid'),
                'context': values.get('Context'),
                'connected_line_num': values.get('ConnectedLineNum'),
                'connected_line_name': values.get('ConnectedLineName'),
                'state': values.get('ChannelState'),
                'state_desc': values.get('ChannelStateDesc'),
                'exten': values.get('Exten'),
                'callerid_num': values.get('CallerIDNum'),
                'callerid_name': values.get('CallerIDName'),
                'accountcode': values.get('AccountCode'),
                'priority': values.get('Priority'),
                'app': values.get('Application'),
                'app_data': values.get('AppData'),
        })
        else:
            _logger.warning('No channel {} found for state update.'.format(
            values.get('Uniqueid')))
        self.env['bus.bus'].sendone('asterisk_channels', 'message');
        return True


    @api.model
    def hangup_channel(self, values):
        uniqueid = values.get('Uniqueid')
        channel = values.get('Channel')
        found = self.env['asterisk.channel'].search([('uniqueid', '=', uniqueid)])
        if found:
            _logger.debug('Found channel {}'.format(channel))
            found.unlink()
        else:
            _logger.warning('Channel {} not found for hangup.'.format(uniqueid))
        self.env['bus.bus'].sendone('asterisk_channels', 'message');
        return True
