import paho.mqtt.client as mqtt
import socket
import os

# Define Variables
AST_ETC_DIR= "/etc/asterisk"
MQTT_HOST = "broker"
MQTT_PORT = 1883
MQTT_KEEPALIVE_INTERVAL = 45
HOSTNAME = socket.gethostname()

def on_connect(client, userdata, flags, rc):
    client.subscribe("%s/#" % HOSTNAME)

def on_message(client, userdata, msg):
    print 'Unhandled msg received with topic %s' % msg.topic

def on_file(client, userdata, msg):
    filename = os.path.join(AST_ETC_DIR, msg.topic.split('/')[2])
    print 'Updating file %s' % filename
    with open(filename, 'w') as f:
        f.write(msg.payload)

# Initiate MQTT Client
mqttc = mqtt.Client()

# Register publish callback function
mqttc.on_connect = on_connect
mqttc.on_message = on_message
mqttc.message_callback_add("%s/file/+" % HOSTNAME, on_file)

# Connect with MQTT Broker
mqttc.connect(MQTT_HOST, MQTT_PORT, MQTT_KEEPALIVE_INTERVAL)

# Loop forever
mqttc.loop_forever()
