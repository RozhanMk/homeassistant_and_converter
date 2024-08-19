import paho.mqtt.client as mqtt
import serial
import time
from settings import *

# MQTT configuration
MQTT_BROKER = "core-mosquitto"
MQTT_PORT = 1883
SERIAL_PORT = '/dev/ttyS0'
BAUDRATE = 115200

LIGHT_TOPIC_COMMANDS = {
    SWITCH1_COMMAND_TOPIC: [5, 1, 1],
    SWITCH2_COMMAND_TOPIC: [5, 1, 2],
    SWITCH3_COMMAND_TOPIC: [5, 1, 4],
    SWITCH4_COMMAND_TOPIC: [5, 1, 8]
}

general_mode = 4
ser = serial.Serial(port=SERIAL_PORT, baudrate=BAUDRATE, timeout=1)  # test different timeouts


def on_connect(client, userdata, flags, rc):
    print(f"Connected to MQTT broker with result code {rc}")
    for topic in LIGHT_TOPIC_COMMANDS.keys():
        client.subscribe(topic)
    client.subscribe(MODE_COMMAND_TOPIC)
    client.subscribe(FAN_COMMAND_TOPIC)
    client.subscribe(TEMP_COMMAND_TOPIC)

def on_message(client, userdata, msg):
    print(f"Message received: {msg.topic} {msg.payload.decode()}")
    if msg.topic in LIGHT_TOPIC_COMMANDS:
        light_commands = {
            "1": LIGHT_TOPIC_COMMANDS.get(msg.topic, []),
            "0": [LIGHT_TOPIC_COMMANDS.get(msg.topic, [])[0] , 2, LIGHT_TOPIC_COMMANDS.get(msg.topic, [])[2]]
        }
        command = light_commands.get(msg.payload.decode())
        if command:
            send_can_message(command)
            
    elif msg.topic == MODE_COMMAND_TOPIC:
        mode = msg.payload.decode()
        set_mode(client, mode)
    elif msg.topic == FAN_COMMAND_TOPIC:
        fan_mode = msg.payload.decode()
        set_fan_mode(client, fan_mode)
    elif msg.topic == TEMP_COMMAND_TOPIC:
        temp = float(msg.payload.decode())
        set_temperature(client, temp)



def set_mode(client, mode):
    print(f"Setting mode to {mode}")
    command = None
    if mode == "heat":
        command = [125, 7, 2]
    elif mode == "cool":
        command = [125, 7, 1]
    elif mode == "auto":
        print(f"general mode = {general_mode}")
        command = [125, 0, general_mode + 32]
    elif mode == "off":
        command = [125, 7, 0]
    
    if command:
        send_can_message(command)
    client.publish(MODE_STATE_TOPIC, mode)

def set_fan_mode(client, fan_mode):
    print(f"Setting fan mode to {fan_mode}")
    command = None
    if fan_mode == "high":
        command = [125, 6, 3]
    elif fan_mode == "medium":
        command = [125, 6, 2]
    elif fan_mode == "low":
        command = [125, 6, 1]
    elif fan_mode == "off":
        command = [125, 6, 0]
    
    if command:
        send_can_message(command)
    client.publish(FAN_STATE_TOPIC, fan_mode)

def set_temperature(client, temp):
    print(f"Setting temperature to {temp}")
    command = [125, 3, temp*2]
    send_can_message(command)
    client.publish(TEMP_STATE_TOPIC, temp)

def send_can_message(command):
    ser.write(command)
    ser.flush()
    time.sleep(0.2) # wait a bit to complete sending the command

def publish_status(client):
    try:
        while True:
            if ser.in_waiting >= 5:
                line = ser.read(5)
                received_data = [int(x) for x in line]
            
                print(', '.join(map(str, received_data)))
                if received_data[:3] == [64, 5, 0] and received_data[4] == 37:  # 4 switch lights
                    light_byte = received_data[3]
                    light_statuses = {
                        SWITCH1_STATE_TOPIC: "1" if light_byte & 1 else "0",
                        SWITCH2_STATE_TOPIC: "1" if light_byte & 2 else "0",
                        SWITCH3_STATE_TOPIC: "1" if light_byte & 4 else "0",
                        SWITCH4_STATE_TOPIC: "1" if light_byte & 8 else "0"
                    }
                    for topic, status in light_statuses.items():
                        client.publish(topic, status)
                elif received_data[:2] == [64, 125] and received_data[4] == 37:
                    publish_hvac_state(client, received_data)

    except serial.SerialException as e:
        print(f"Error: {e}")
    except KeyboardInterrupt:
        print("Stopping serial read.")
    finally:
        print("Serial reading port closed.")
        ser.close()

def publish_hvac_state(client, received_data):
    hvac_bytes = received_data[3]
    if received_data[2] == 0:   # register 0
        if hvac_bytes & 3 == 0:
            fan_mode = "off"
        elif hvac_bytes & 3 == 1:
            fan_mode = "low"
        elif hvac_bytes & 3 == 2:
            fan_mode = "medium"
        elif hvac_bytes & 3 == 3:
            fan_mode = "high"
        if (hvac_bytes & 12) >> 2 == 0:
            mode = "off"
        elif (hvac_bytes & 12) >> 2 == 1:
            mode = "cool"
        elif (hvac_bytes & 12) >> 2 == 2:
            mode = "heat"
        if (hvac_bytes & 48) >> 4 == 2:
            mode = "auto"
        global general_mode
        general_mode = (hvac_bytes & 12)
        client.publish(MODE_STATE_TOPIC, mode)
        client.publish(FAN_STATE_TOPIC, fan_mode)

    if received_data[2] == 3:   # register 3
        set_temp = hvac_bytes / 2
        client.publish(TEMP_STATE_TOPIC, int(set_temp))
    if received_data[2] == 2:   # register 2
        current_temp = hvac_bytes
        client.publish(CURRENT_TEMP_TOPIC, current_temp)


client = mqtt.Client()
client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
client.on_connect = on_connect
client.on_message = on_message

client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.loop_start() #start the MQTT client in a separate thread

try:
    publish_status(client)
finally:
    client.loop_stop()
    client.disconnect()