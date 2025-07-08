import serial
import signal
import sys

# UART Configuration
SERIAL_PORT = "/dev/ttyUSB0"
BAUD_RATE = 57600

# Global variable for the serial connection
ser = None

def signal_handler(sig, frame):
    print("\n🔴 Exiting gracefully...")
    if ser and ser.is_open:
        ser.close()
        print("✅ Serial Port Closed.")
    sys.exit(0)

# Register Ctrl+C handler
signal.signal(signal.SIGINT, signal_handler)

try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    print("✅ Serial Port Opened!")
except serial.SerialException:
    print(f"❎ Failed to open serial port {SERIAL_PORT}")
    sys.exit(1)

# Main read loop
print("🟢 Reading from serial port. Press Ctrl+C to stop.")

try:
    while True:
        if ser.in_waiting > 0:
            line = ser.readline().decode('utf-8', errors='replace').strip()
            if line:
                print(f"📥 Received: {line}")
except KeyboardInterrupt:
    signal_handler(None, None)
