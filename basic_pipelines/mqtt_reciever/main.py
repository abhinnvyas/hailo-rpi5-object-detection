import paho.mqtt.client as mqtt
import subprocess

# Track process handles
processes = {
    "detection": None,
    "face_recognition": None
}

# Handle start/stop
def handle_program(name, command, action):
    if action.lower() == "on":
        if processes[name] is None:
            processes[name] = subprocess.Popen(command, shell=True)
            print(f"{name} started.")
        else:
            print(f"{name} already running.")
    elif action.lower() == "off":
        if processes[name] is not None:
            processes[name].terminate()
            processes[name] = None
            print(f"{name} stopped.")
        else:
            print(f"{name} not running.")

# MQTT message handler
def on_message(client, userdata, msg):
    topic = msg.topic
    payload = msg.payload.decode().strip().lower()
    print(f"[MQTT] {topic}: {payload}")

    if topic == "app/control/detection":
        handle_program("detection", "python3 detection.py", payload)
    elif topic == "app/control/face_recognition":
        handle_program("face_recognition", "python3 ../venv_hailo_rpi_examples/lib64/python3.11/site-packages/hailo_apps/hailo_app_python/apps/face_recognition/face_recognition.py", payload)

# MQTT setup
client = mqtt.Client()
client.on_message = on_message

client.connect("localhost", 1883, 60)  # Add authentication if needed

# Topics
client.subscribe("app/control/detection")
client.subscribe("app/control/face_recognition")

print("MQTT Controller running...")
client.loop_forever()
