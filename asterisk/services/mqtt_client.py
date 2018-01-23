import gevent
from gevent import monkey; monkey.patch_all()
from gevent import sleep
from gevent.queue import Queue
from gevent.event import Event
import json
import logging
import paho.mqtt.client as mqtt
import re
import socket
import subprocess
import os
import uuid
from odoo_broker import OdooBroker
from odoorpc.error import RPCError

# Define Variables
AST_ETC_DIR= "/etc/asterisk"
ASTERISK_BINARY = os.environ.get('ASTERISK_BINARY', '/usr/sbin/asterisk')
MQTT_HOST = "broker"
MQTT_PORT = 1883
MQTT_KEEPALIVE_INTERVAL = 45
HOSTNAME = socket.gethostname()
ASTERISK_COMMANDS_DELAY = 3 # seconds to wait for more commands to come

asterisk_conf_apply_commands = {
    'sip.conf': 'sip reload',
    'extensions.conf': 'dialplan reload',
}

logging.basicConfig(level=logging.DEBUG)

class Client:
    asterisk_commands_queue = []
    asterisk_commands_flag = Event()

    def __init__(self):
        self.uid = os.environ.get('UID') or '{}'.format(uuid.getnode())
        logging.info('UID: ' + self.uid)
        self.mqtt_client = mqtt.Client(client_id=self.uid)
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message
        self.mqtt_client.on_publish = self.on_publish
        self.mqtt_client.on_subscribe = self.on_subscribe
        self.mqtt_client.on_log = self.on_log
        # Subscribe to myself
        self.mqtt_client.connect(MQTT_HOST, MQTT_PORT, MQTT_KEEPALIVE_INTERVAL)
        self.mqtt_client.subscribe('asterisk/' + self.uid + '/#', 0)
        # Connecto to Odoo
        self.odoo_broker = OdooBroker()
        # Spawn
        gevent.spawn(self.asterisk_commands_worker)
        gevent.spawn(self.register_server)
        # Send registration request
        self.mqtt_client.publish('odoo/register/{}'.format(self.uid), '')
        gevent.joinall([gevent.spawn(self.mqtt_client.loop_forever)])


    def register_server(self):
        self.odoo_broker.odoo_connected.wait()
        server_id = self.odoo_broker.odoo.env['asterisk.server'].search(
                                            [('uid','=', self.uid)])
        if server_id:
            self.server_id  = server_id[0]
            logging.info('Server found, id {}.'.format(self.server_id))
        else:
            # New server, create one and request configs
            self.server_id = self.odoo_broker.odoo.env['asterisk.server'].create({
                'uid': self.uid,
                'name': self.uid,
            })
            logging.info('Server {} created, sending configs.'.format(self.server_id))
            self.upload_asterisk_configs()


    def upload_asterisk_config(self, conf):
        # Check if conf file already exists
        file_id = self.odoo_broker.odoo.env['asterisk.conf'].search([
            ('server', '=', self.server_id),
            ('name', '=', conf)
        ])
        try:
            if not file_id:
                logging.debug('Creating remote {}.'.format(conf))
                self.odoo_broker.odoo.env['asterisk.conf'].create({
                    'name': conf,
                    'server': self.server_id,
                    'content': open(os.path.join(AST_ETC_DIR, conf)).read()
                })
            else:
                logging.debug('Updating remote {}.'.format(conf))
                odoo_conf = self.odoo_broker.odoo.env['asterisk.conf'].browse(file_id)
                odoo_conf.write({
                    'name': conf,
                    'server': self.server_id,
                    'content': open(os.path.join(AST_ETC_DIR, conf)).read()
                })
        except UnicodeDecodeError as e:
            logging.error('Skipping file {} due to error: {}'.format(conf, e))



    def upload_asterisk_configs(self):
        conf_files = os.listdir(AST_ETC_DIR)
        for conf in conf_files:
            self.upload_asterisk_config(conf)


    def asterisk_commands_worker(self):
        """
        This workers sleeps until is notified that some commands must be sent
        to Asterisk. After that he wakes up and waits a bit for more commands to
        come and executes them.
        """
        logging.debug('Started asterisk commands worker.')
        while True:
            # Block here untill the 1-st command arrives
            self.asterisk_commands_flag.wait()
            # Now sleep  while to let other command to arrive
            gevent.sleep(ASTERISK_COMMANDS_DELAY)
            # If we have a reload then ignore all other commands
            if self.asterisk_commands_queue.count('reload'):
                # Empty the queue
                self.asterisk_commands_queue = []
                logging.debug('Calling asterisk reload.')
                subprocess.check_call([ASTERISK_BINARY, '-rx', 'reload'])
            else:
                while len(self.asterisk_commands_queue):
                    # Pop commands and apply one by one
                    cmd = self.asterisk_commands_queue.pop()
                    logging.debug('Calling asterisk {}.'.format(cmd))
                    subprocess.check_call([ASTERISK_BINARY, '-rx', cmd])
                # CLear the flag
            self.asterisk_commands_flag.clear()


    def on_connect(self, client, userdata, flags, rc):
        logging.info("rc: " + str(rc))


    def on_message(self, client, userdata, msg):
        logging.info('Topic: {}, Dup: {}, Mid: {}, QoS: {}, Retain: {}, '
                     'State: {}, Info: {}'.format(msg.topic, msg.dup, msg.mid,
                                    msg.qos, msg.retain, msg.state, msg.info))
        found = re.search('^asterisk/{}/(.+)$'.format(self.uid), msg.topic)
        if not found:
            logging.error('Error: topic {} not understood.'.format(msg.topic))
            return
        event_handler = getattr(self, 'on_' + found.group(1), self.handler_not_found)
        gevent.spawn(event_handler, client, userdata, msg)


    def on_publish(self, client, obj, mid):
        logging.info("mid: " + str(mid))


    def on_subscribe(self, client, obj, mid, granted_qos):
        logging.info("Subscribed: " + str(mid) + " " + str(granted_qos))


    def on_log(self, client, obj, level, string):
        logging.info(string)


    def handler_not_found(self, client, userdata, msg):
        logging.error('Topic {} handler not found.'.format(msg.topic))


    def _extract_message(self, payload):
        try:
            msg = json.loads(payload)
            return msg
        except ValueError as e:
            logging.error(e.message, ': ', payload)


    def on_registration_status(self, client, userdata, msg):
        logging.debug('Registration status')
        logging.debug(msg.payload)


    def on_file(self, client, userdata, msg):
        data = self._extract_message(msg.payload)
        logging.debug(data)
        file_name = data.get('Name')
        dest_folder = data.get('DestinationFolder')
        file_path = os.path.join(dest_folder, file_name)
        logging.info('Updating file %s' % file_path)
        with open(file_path, 'w') as f:
            f.write(data.get('Content'))
        # Apply conf
        if dest_folder == AST_ETC_DIR:
            cmd = asterisk_conf_apply_commands.get(file_name, 'reload')
            # Check there is no command already in commands queue
            if not self.asterisk_commands_queue.count(cmd):
                self.asterisk_commands_queue.append(cmd)
                self.asterisk_commands_flag.set()


    def on_upload_asterisk_configs(self, client, userdata, msg):
        self.upload_asterisk_configs()


    def on_sip_reload(self, client, userdata, msg):
        logging.info('SIP reload')


# Initiate MQTT Client
mqttc = Client()
