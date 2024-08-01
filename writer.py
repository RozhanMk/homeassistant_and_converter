import serial
import time

def write_serial(port='/dev/ttyS0', baudrate=115200):
    try:
        ser = serial.Serial(port, baudrate)
        print(f"Connected to {port} at {baudrate} baud to write")
    except serial.SerialException as e:
        print(f"Error: {e}")
        return

    try:
        while True:
            ser.write([5, 0, 2])
            time.sleep(1)
            ser.write([5, 0, 0])
    except KeyboardInterrupt:
        print("Stopping serial write.")
    finally:
        ser.close()
        print("Serial writing port closed.")

if __name__ == "__main__":
    write_serial()