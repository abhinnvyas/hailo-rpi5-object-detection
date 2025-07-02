from pymavlink import mavutil

# Open UART where Herelink Air unit is connected
master = mavutil.mavlink_connection('/dev/ttyAMA0', baud=57600)

while True:
    msg = master.recv_match(type='SERIAL_CONTROL', blocking=True)
    if not msg:
        continue

    if msg.data:
        command = msg.data.decode('utf-8').strip()
        print(f"Received command: {command}")

        if command == "start":
            print("Starting the system!")
            # Call your start routine here

        elif command == "stop":
            print("Stopping the system!")
            # Call your stop routine here
