import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib

import os
import numpy as np
import cv2
import hailo
import base64
import json
import paho.mqtt.client as mqtt

from hailo_apps_infra.hailo_rpi_common import (
    get_caps_from_pad,
    get_numpy_from_buffer,
    app_callback_class,
)
from hailo_apps_infra.detection_pipeline import GStreamerDetectionApp

# ---------------------- MQTT Configuration ----------------------
MQTT_BROKER = "85ad5e2bc01647b994c1740438b3c4f8.s1.eu.hivemq.cloud"      # e.g., "broker.hivemq.com"
MQTT_PORT = 8883                     # or 8883 for TLS
MQTT_TOPIC = "app/detection"
MQTT_USERNAME = "hivemq.webclient.1753169368616"
MQTT_PASSWORD = "EB<0!.*im5AyDCFarb12"

mqtt_client = mqtt.Client()
mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)

# ---------------------- Custom Callback Class ----------------------
class user_app_callback_class(app_callback_class):
    def __init__(self):
        super().__init__()
        self.sent_track_ids = set()
        self.new_variable = 42

    def new_function(self):
        return "The meaning of life is: "

# ---------------------- Callback Function ----------------------
def app_callback(pad, info, user_data):
    buffer = info.get_buffer()
    if buffer is None:
        return Gst.PadProbeReturn.OK

    user_data.increment()
    string_to_print = f"Frame count: {user_data.get_count()}\n"

    format, width, height = get_caps_from_pad(pad)
    frame = None
    if user_data.use_frame and format and width and height:
        frame = get_numpy_from_buffer(buffer, format, width, height)

    roi = hailo.get_roi_from_buffer(buffer)
    detections = roi.get_objects_typed(hailo.HAILO_DETECTION)

    detection_count = 0
    for detection in detections:
        label = detection.get_label()
        bbox = detection.get_bbox()
        confidence = detection.get_confidence()

        # Get track ID (if any)
        track_id = 0
        track = detection.get_objects_typed(hailo.HAILO_UNIQUE_ID)
        if len(track) == 1:
            track_id = track[0].get_id()

        # Classify into person or animal
        if label.lower() == "person":
            detection_type = "person"
        elif label.lower() in ["dog", "cat", "horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe"]:  # Add more if needed
            detection_type = "animal"
        else:
            continue  # skip other labels

        string_to_print += f"Detection: ID: {track_id} Type: {detection_type} Label: {label} Confidence: {confidence:.2f}\n"
        detection_count += 1

        if user_data.use_frame and frame is not None:
            unique_key = f"{detection_type}_{track_id}"
            if unique_key not in user_data.sent_track_ids:
                # Convert to JPEG
                success, jpeg = cv2.imencode('.jpg', frame)
                if success:
                    b64_bytes = base64.b64encode(jpeg.tobytes()).decode('utf-8')
                    payload = {
                        "type": detection_type,
                        "message": f"{label.capitalize()} detected with track ID {track_id}",
                        "image": b64_bytes,
                        "confidence": round(confidence, 2)
                    }
                    mqtt_client.publish(MQTT_TOPIC, json.dumps(payload))
                    user_data.sent_track_ids.add(unique_key)

    if user_data.use_frame and frame is not None:
        cv2.putText(frame, f"Detections: {detection_count}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(frame, f"{user_data.new_function()} {user_data.new_variable}", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        user_data.set_frame(frame)

    print(string_to_print)
    return Gst.PadProbeReturn.OK

# ---------------------- Main App Runner ----------------------
if __name__ == "__main__":
    Gst.init(None)
    user_data = user_app_callback_class()
    app = GStreamerDetectionApp(app_callback, user_data)
    app.run()
