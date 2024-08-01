import serial
import time

def read_serial(port='/dev/ttyS0', baudrate=115200):
    updated_received_data = list()
    counter = 0
    try:
        ser = serial.Serial(port, baudrate, timeout=0)
        print(f"Connected to {port} at {baudrate} baud to read")
    except serial.SerialException as e:
        print(f"Error: {e}")
        return

    try:
        while True:
            if ser.in_waiting > 0:
                line = int(ser.read(1)[0])
                updated_received_data.append(line)
                counter += 1
            if counter == 5:
                counter = 0
                for bit in updated_received_data:
                    print(bit, end=", ")
                print("\n")
                updated_received_data.clear()
    except KeyboardInterrupt:
        print("Stopping serial read.")
    finally:
        ser.close()
        print("Serial reading port closed.")

if __name__ == "__main__":
    read_serial()