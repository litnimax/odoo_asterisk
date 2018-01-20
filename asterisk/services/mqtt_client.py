import json
import paho.mqtt.client as mqtt
import re
import socket
import os
import uuid

# Define Variables
AST_ETC_DIR= "/etc/asterisk"
MQTT_HOST = "broker"
MQTT_PORT = 1883
MQTT_KEEPALIVE_INTERVAL = 45
HOSTNAME = socket.gethostname()



class Client():

    def __init__(self):
        self.uid = os.environ.get('UID') or '{}'.format(uuid.getnode())
        print 'UID: ' + self.uid
        self.mqtt_client = mqtt.Client(client_id=self.uid)
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message
        self.mqtt_client.on_publish = self.on_publish
        self.mqtt_client.on_subscribe = self.on_subscribe
        self.mqtt_client.on_log = self.on_log
        # Subscribe to myself
        self.mqtt_client.connect(MQTT_HOST, MQTT_PORT, MQTT_KEEPALIVE_INTERVAL)
        self.mqtt_client.subscribe('/asterisk/' + self.uid + '/#', 0)
        self.mqtt_client.loop_forever()



    def on_connect(self, client, userdata, flags, rc):
        print("rc: " + str(rc))


    def on_message(self, client, userdata, msg):
        print(msg.info, msg.dup, msg.mid, msg.qos, msg.retain, msg.state, msg.timestamp, msg.topic)
        found = re.search('^/asterisk/{}/(.+)$'.format(self.uid), msg.topic)
        if not found:
            print('Error: topic {} not understood.'.format(msg.topic))
        event_handler = getattr(self, 'on_' + found.group(1), self.handler_not_found)
        event_handler(client, userdata, msg)

    def on_publish(self, client, obj, mid):
        print("mid: " + str(mid))


    def on_subscribe(self, client, obj, mid, granted_qos):
        print("Subscribed: " + str(mid) + " " + str(granted_qos))


    def on_log(self, client, obj, level, string):
        print(string)


    def handler_not_found(self, client, userdata, msg):
        print 'Topic {} handler not found.'.format(msg.topic)


    def _extract_message(self, payload):
        try:
            msg = json.loads(payload)
            return msg
        except ValueError as e:
            print(e.message, ': ', payload)


    def on_file(self, client, userdata, msg):
        data = self._extract_message(msg.payload)
        file_name = data.get('FileName')
        dest_folder = data.get('DestinationFolder')
        filename = os.path.join(dest_folder, file_name)
        print 'Updating file %s' % filename
        with open(filename, 'w') as f:
            f.write(data.get('Content'))



# Initiate MQTT Client
mqttc = Client()
