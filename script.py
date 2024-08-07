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
    SWITCH1_TOPIC_SUBSCRIBE: [5, 1, 1],
    SWITCH2_TOPIC_SUBSCRIBE: [5, 1, 2],
    SWITCH3_TOPIC_SUBSCRIBE: [5, 1, 4],
    SWITCH4_TOPIC_SUBSCRIBE: [5, 1, 8]
}

def on_connect(client, userdata, flags, rc):
    print(f"Connected to MQTT broker with result code {rc}")
    for topic in TOPIC_COMMANDS.keys():
        client.subscribe(topic)

def on_message(client, userdata, msg):
    print(f"Message received: {msg.topic} {msg.payload.decode()}")
    topic_commands = {
        "1": TOPIC_COMMANDS.get(msg.topic, []),
        "0": TOPIC_COMMANDS.get(msg.topic, [])[0] + [2] + TOPIC_COMMANDS.get(msg.topic, [])[2]
    }
    command = topic_commands.get(msg.payload.decode())
    if command:
        send_can_message(command)
    time.sleep(1)

def send_can_message(command):
    try:
        with serial.Serial(SERIAL_PORT, BAUDRATE) as ser:
            print(f"Connected to {SERIAL_PORT} at {BAUDRATE} baud to write.")
            ser.write(command)
    except serial.SerialException as e:
        print(f"Error: {e}")
    finally:
        print("Serial writing port closed.")

def publish_light_status(client):
    try:
        with serial.Serial(SERIAL_PORT, BAUDRATE) as ser:
            print(f"Connected to {SERIAL_PORT} at {BAUDRATE} baud to read.")
            updated_received_data = []
            counter = 0
            light_status = "0"

            while True:
                if ser.in_waiting > 0:
                    line = int(ser.read(1)[0])
                    updated_received_data.append(line)
                    counter += 1

                if counter == 5:
                    counter = 0
                    # debug
                    print(', '.join(map(str, updated_received_data)))
                    if updated_received_data[:3] == [64, 5, 0] and updated_received_data[4] == 37:
                        light_byte = updated_received_data[3]
                        light_statuses = {
                            SWITCH1_TOPIC_PUBLISH: "1" if light_byte & 1 else "0",
                            SWITCH2_TOPIC_PUBLISH: "1" if light_byte & 2 else "0",
                            SWITCH3_TOPIC_PUBLISH: "1" if light_byte & 4 else "0",
                            SWITCH4_TOPIC_PUBLISH: "1" if light_byte & 8 else "0"
                        }

                    for topic, status in light_statuses.items():
                        client.publish(topic, status)

                    updated_received_data.clear()
    except serial.SerialException as e:
        print(f"Error: {e}")
    except KeyboardInterrupt:
        print("Stopping serial read.")
    finally:
        print("Serial reading port closed.")

client = mqtt.Client()
client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
client.on_connect = on_connect
client.on_message = on_message

client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.loop_start()

publish_light_status(client)