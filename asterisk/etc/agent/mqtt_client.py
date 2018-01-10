import paho.mqtt.client as mqtt

# Define Variables
MQTT_HOST = "broker"
MQTT_PORT = 1883
MQTT_KEEPALIVE_INTERVAL = 45
HOSTNAME = "112233445566"

def on_connect(client, userdata, flags, rc):
    client.subscribe("%s/#" % HOSTNAME)

def on_message(client, userdata, msg):
    print 'Unhandled msg received with topic %s' % msg.topic

def update_config(client, userdata, msg):
    filename = msg.topic.split('/')[2]
    print 'Going to update config file %s' % filename
    with open('/etc/asterisk/%s' % filename, 'w') as f:
        f.write(msg.payload)

# Initiate MQTT Client
mqttc = mqtt.Client()

# Register publish callback function
mqttc.on_connect = on_connect
mqttc.on_message = on_message
mqttc.message_callback_add("%s/conf/+" % HOSTNAME, update_config)

# Connect with MQTT Broker
mqttc.connect(MQTT_HOST, MQTT_PORT, MQTT_KEEPALIVE_INTERVAL)

# Loop forever
mqttc.loop_forever()
