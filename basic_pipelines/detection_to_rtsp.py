import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
import os
import numpy as np
import cv2
import hailo

from hailo_apps_infra.hailo_rpi_common import (
    get_caps_from_pad,
    get_numpy_from_buffer,
    app_callback_class,
)
from hailo_apps_infra.detection_pipeline import GStreamerDetectionApp

# -----------------------------------------------------------------------------------------------
# Define the pipeline components manually
# -----------------------------------------------------------------------------------------------

def SOURCE_PIPELINE(source="/dev/video0", width=640, height=480):
    return f"v4l2src device={source} ! video/x-raw, width={width}, height={height}, format=YUY2 ! videoconvert"

def INFERENCE_PIPELINE(model_path="/home/pi/yolov5.hef"):
    return f"hailonet hef-path={model_path} ! hailofilter"

def INFERENCE_PIPELINE_WRAPPER(inner):
    return f"{inner}"

def TRACKER_PIPELINE(class_id=1):
    return f"hailotracker class-id={class_id}"

def USER_CALLBACK_PIPELINE():
    return "appsink name=appsink emit-signals=true"

# -----------------------------------------------------------------------------------------------
# Custom Detection App
# -----------------------------------------------------------------------------------------------

class CustomDetectionApp(GStreamerDetectionApp):
    def get_pipeline_string(self):
        pipeline_string = (
            f'{SOURCE_PIPELINE(self.video_source, self.video_width, self.video_height)} ! '
            f'{INFERENCE_PIPELINE_WRAPPER(INFERENCE_PIPELINE())} ! '
            f'{TRACKER_PIPELINE(class_id=1)} ! '
            f'{USER_CALLBACK_PIPELINE()} ! '
            f'videoconvert ! x264enc tune=zerolatency bitrate=500 speed-preset=superfast ! '
            f'rtph264pay config-interval=1 pt=96 ! udpsink host=127.0.0.1 port=5000'
        )
        print(pipeline_string)
        return pipeline_string

# -----------------------------------------------------------------------------------------------
# User-defined app callback class
# -----------------------------------------------------------------------------------------------

class user_app_callback_class(app_callback_class):
    def __init__(self):
        super().__init__()
        self.new_variable = 42

    def new_function(self):
        return "The meaning of life is: "

# -----------------------------------------------------------------------------------------------
# Callback function
# -----------------------------------------------------------------------------------------------

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
        if label == "person":
            track_id = 0
            track = detection.get_objects_typed(hailo.HAILO_UNIQUE_ID)
            if len(track) == 1:
                track_id = track[0].get_id()
            string_to_print += (f"Detection: ID: {track_id} Label: {label} Confidence: {confidence:.2f}\n")
            detection_count += 1

    if user_data.use_frame:
        cv2.putText(frame, f"Detections: {detection_count}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(frame, f"{user_data.new_function()} {user_data.new_variable}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        user_data.set_frame(frame)

    print(string_to_print)
    return Gst.PadProbeReturn.OK

# -----------------------------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------------------------

if __name__ == "__main__":
    user_data = user_app_callback_class()
    app = CustomDetectionApp(app_callback, user_data)
    app.run()
