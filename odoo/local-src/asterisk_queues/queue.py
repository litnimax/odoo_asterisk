import json
import logging
from openerp import models, fields, api, _

logger = logging.getLogger(__name__)


OPERATOR_STATES = [
        ('disconnected', 'disconnected'),
        ('ready', 'ready'),
        ('oncall', 'oncall'),
        ('onhold', 'onhold'),
        ('kicked', 'kicked')
]

QUEUE_CALL_STATES = [
        ('waiting', 'Waiting'),
        ('onhold', 'On Hold'),
        ('complete', 'Completed'),
        ('abondon', 'Abondon'),
]


"""
grant all on asterisk_queue to asterisk;
GRANT
asterisk=# grant all on asterisk_queue_member to asterisk;
GRANT
asterisk=# grant all on asterisk_queue_rule to asterisk;
GRANT
"""


ASTERISK_CMD_URL = 'tcp://192.168.56.101:1967'
import zmq.green as zmq
# Asterisk commands
def asterisk_action(action):
    """
    :param action: {'Action': 'Name', ...}
    :return: reply from Asterisk
    """
    logger.debug('Sending action %s to %s' % (action.get('Action'),
                                              ASTERISK_CMD_URL))
    # Asterisk CMD socket
    context = zmq.Context.instance()
    sock = context.socket(zmq.REQ)
    sock.setsockopt(zmq.LINGER, 0)
    sock.connect(ASTERISK_CMD_URL)
    poll = zmq.Poller()
    try:
        poll.register(sock, zmq.POLLIN)
        sock.send(json.dumps(action))
        socks = dict(poll.poll(1000)) # 1 seconds to reply!
        if socks.get(sock) == zmq.POLLIN:
            reply = sock.recv_json()
            logger.debug('Asterisk reply: %s' % json.dumps(reply, indent=2,
                                                           sort_keys=True))
            return reply
        else:
            logger.error('Asterisk did not reply! Action: %s' % json.dumps(
                                            action, indent=2, sort_keys=True))

    except zmq.ZMQError, e:
        logger.error('Asterisk command ZMQError: %s' % e)

    finally:
        poll.unregister(sock)
        sock.close()




class Queue(models.Model):
    _name = 'asterisk.queue'
    _description = 'Queue'
    _inherit = ['mail.thread', 'ir.needaction_mixin']

    name = fields.Char(required=True, index=True)
    operators = fields.Many2many(comodel_name='asterisk.operator')
    calls = fields.One2many('asterisk.queue_call', inverse_name='queue')




class QueueCall(models.Model):
    _name = 'asterisk.queue_call'
    _description = 'Queue Call'
    _rec_name = 'caller_number'

    queue = fields.Many2one('asterisk.queue', required=True)
    resident = fields.Many2one('asterisk.resident')
    caller_number = fields.Char(required=True)
    state = fields.Selection(QUEUE_CALL_STATES)
    states = fields.One2many(comodel_name='asterisk.queue_call_log',
                             inverse_name='call')
    channel_id = fields.Char(index=True, required=True)
    channel_name = fields.Char(index=True)


    @api.multi
    def unlink(self):
        try:
            asterisk_action({
                'Action': 'Hangup',
                'Channel': self.channel_name,
                'Cause': '16',
            })

        except Exception as e:
            logger.exception('Queue call ulink error:')

        finally:
            super(QueueCall, self).unlink()



    @api.multi
    def hangup(self):
        self.ensure_one()
        self.unlink()



class QueueCallLog(models.Model):
    _name = 'asterisk.queue_call_log'
    _description = 'Queue Call Log'

    call = fields.Many2one('asterisk.queue_call')
    prev_state = fields.Selection(QUEUE_CALL_STATES)
    next_state = fields.Selection(QUEUE_CALL_STATES)
    change_date = fields.Datetime()



class Operator(models.Model):
    _name = 'asterisk.operator'
    _description = 'Operator'

    name = fields.Char(required=True, index=True)
    exten = fields.Char(required=True)
    queues = fields.Many2many(comodel_name='asterisk.queue')
    state = fields.Selection(OPERATOR_STATES, default='disconnected')
    states = fields.One2many(comodel_name='asterisk.operator_log',
                             inverse_name='operator')




class OperatorLog(models.Model):
    _name = 'asterisk.operator_log'
    _description = 'Operator Log'

    operator = fields.Many2one('asterisk.operator')
    prev_state = fields.Selection(OPERATOR_STATES)
    next_state = fields.Selection(OPERATOR_STATES)
    change_date = fields.Datetime()
