import serial
import time

# === CONFIGURATION ===
SERIAL_PORT = '/dev/serial0'   # Or /dev/ttyAMA0, /dev/ttyS0, etc.
BAUD_RATE = 115200
TIMEOUT = 1  # seconds

def main():
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=TIMEOUT)
        print(f"✅ Serial port {SERIAL_PORT} opened at {BAUD_RATE} baud.")

        while True:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='replace').strip()
                print(f"📨 Received: {line}")

            time.sleep(0.1)

    except serial.SerialException as e:
        print(f"❌ Serial error: {e}")
    except KeyboardInterrupt:
        print("\n🛑 Exiting.")
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print(f"✅ Serial port {SERIAL_PORT} closed.")

if __name__ == '__main__':
    main()
