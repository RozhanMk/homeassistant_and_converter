import paho.mqtt.client as mqtt
import serial
import time
from settings import *

# MQTT configuration
MQTT_BROKER = "core-mosquitto"
MQTT_PORT = 1883
SERIAL_PORT = '/dev/ttyS0'
BAUDRATE = 115200

TOPIC_COMMANDS = {
    SWITCH1_COMMAND_TOPIC: [5, 1, 1],
    SWITCH2_COMMAND_TOPIC: [5, 1, 2],
    SWITCH3_COMMAND_TOPIC: [5, 1, 4],
    SWITCH4_COMMAND_TOPIC: [5, 1, 8]
}

ser = serial.Serial(port=SERIAL_PORT, baudrate=BAUDRATE, timeout=1) # test different timeouts

def on_connect(client, userdata, flags, rc):
    print(f"Connected to MQTT broker with result code {rc}")
    for topic in TOPIC_COMMANDS.keys():
        client.subscribe(topic)

def on_message(client, userdata, msg):
    print(f"Message received: {msg.topic} {msg.payload.decode()}")
    topic_commands = {
        "1": TOPIC_COMMANDS.get(msg.topic, []),
        "0": [TOPIC_COMMANDS.get(msg.topic, [])[0] ,2, TOPIC_COMMANDS.get(msg.topic, [])[2]]
    }
    command = topic_commands.get(msg.payload.decode())
    if command:
        send_can_message(command)

def send_can_message(command):
    try:
        ser.write(command)
        ser.flush()  # Ensure all data is transmitted
        print(f"command written: {command} ")
        time.sleep(0.2) # wait a bit to complete sending the command
    except serial.SerialException as e:
        print(f"Error sending command: {e}")
    
def publish_light_status(client):
    try:
        while True:
            if ser.in_waiting >= 5:  # Check if there's any data in the buffer
                line = ser.read(5)
                received_data = [int(x) for x in line]

                print(', '.join(map(str, received_data)))
                if received_data[:3] == [64, 5, 0] and received_data[4] == 37:
                    light_byte = received_data[3]
                    light_statuses = {
                        SWITCH1_STATE_TOPIC: "1" if light_byte & 1 else "0",
                        SWITCH2_STATE_TOPIC: "1" if light_byte & 2 else "0",
                        SWITCH3_STATE_TOPIC: "1" if light_byte & 4 else "0",
                        SWITCH4_STATE_TOPIC: "1" if light_byte & 8 else "0"
                    }

                    for topic, status in light_statuses.items():
                        client.publish(topic, status)
        
    except serial.SerialException as e:
        print(f"Error: {e}")
    except KeyboardInterrupt:
        print("Stopping serial read.")
    finally:
        print("Serial reading port closed.")
        ser.close()

client = mqtt.Client()
client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
client.on_connect = on_connect
client.on_message = on_message

client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.loop_start() #start the MQTT client in a separate thread

try:
    publish_light_status(client)
finally:
    client.loop_stop()
    client.disconnect()