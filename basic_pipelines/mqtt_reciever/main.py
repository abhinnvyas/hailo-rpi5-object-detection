import paho.mqtt.client as mqtt
import subprocess
import os
import signal
import ssl

# Track process handles
processes = {
    "detection": None,
    "face_recognition": None
}

# Stop the other process if it’s running
def stop_other_program(current_name):
    for name in processes:
        if name != current_name and processes[name] is not None:
            print(f"Stopping other program: {name}")
            try:
                os.killpg(os.getpgid(processes[name].pid), signal.SIGTERM)
                processes[name] = None
                print(f"{name} stopped.")
            except Exception as e:
                print(f"Error stopping {name}: {e}")

# Handle starting and stopping programs
def handle_program(name, command, action):
    action = action.lower()
    
    if action == "on":
        if processes[name] is None:
            stop_other_program(name)
            try:
                processes[name] = subprocess.Popen(command, shell=True, preexec_fn=os.setsid)
                print(f"[{name}] started.")
            except Exception as e:
                print(f"Error starting {name}: {e}")
        else:
            print(f"[{name}] is already running.")
    
    elif action == "off":
        if processes[name] is not None:
            try:
                os.killpg(os.getpgid(processes[name].pid), signal.SIGTERM)
                processes[name] = None
                print(f"[{name}] stopped.")
            except Exception as e:
                print(f"Error stopping {name}: {e}")
        else:
            print(f"[{name}] is not running.")

# MQTT callback
def on_message(client, userdata, msg):
    topic = msg.topic
    payload = msg.payload.decode().strip().lower()
    print(f"[MQTT] {topic}: {payload}")

    if topic == "app/control/detection":
        handle_program("detection", "python3 ../detection.py", payload)

    elif topic == "app/control/face_recognition":
        handle_program(
            "face_recognition",
            "python3 ../../venv_hailo_rpi_examples/lib64/python3.11/site-packages/hailo_apps/hailo_app_python/apps/face_recognition/face_recognition.py",
            payload
        )

MQTT_BROKER = "85ad5e2bc01647b994c1740438b3c4f8.s1.eu.hivemq.cloud"
MQTT_PORT = 8883  # Use 8883 for secure MQTT over TLS
MQTT_USERNAME = "hivemq.webclient.1753169368616"  # Replace with your HiveMQ Cloud username
MQTT_PASSWORD = "EB<0!.*im5AyDCFarb12"  # Replace with your password

# MQTT setup
client = mqtt.Client()
client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

# Enable TLS for secure connection
client.tls_set(
    ca_certs=None,  # Uses system default CA certificates
    certfile=None,
    keyfile=None,
    cert_reqs=ssl.CERT_REQUIRED,
    tls_version=ssl.PROTOCOL_TLS_CLIENT,
    ciphers=None
)

client.on_message = on_message

# Replace with your broker IP/domain
# MQTT_BROKER = "85ad5e2bc01647b994c1740438b3c4f8.s1.eu.hivemq.cloud"

client.connect(MQTT_BROKER, MQTT_PORT, 60)

# Subscribe to control topics
client.subscribe("app/control/detection")
client.subscribe("app/control/face_recognition")

print("✅ MQTT Controller is running and waiting for commands...")
client.loop_forever()
