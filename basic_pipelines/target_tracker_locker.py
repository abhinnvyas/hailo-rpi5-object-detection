import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
import os
import numpy as np
import cv2
import hailo
import serial
from threading import Thread

from hailo_apps_infra.hailo_rpi_common import (
    get_caps_from_pad,
    get_numpy_from_buffer,
    app_callback_class,
)
from hailo_apps_infra.detection_pipeline import GStreamerDetectionApp

# -----------------------------------------------------------------------------------------------
# User-defined class
# -----------------------------------------------------------------------------------------------
class user_app_callback_class(app_callback_class):
    def __init__(self):
        super().__init__()
        self.new_variable = 42
        self.locked_track_id = None
        self.frame_size = (640, 480)
        self.last_detections = []
        self.last_frame = None

    def new_function(self):
        return "The meaning of life is: "

# -----------------------------------------------------------------------------------------------
# Mouse callback to lock target
# -----------------------------------------------------------------------------------------------
def on_mouse_click(event, x, y, flags, param):
    if event != cv2.EVENT_LBUTTONDOWN:
        return

    frame = param.last_frame
    detections = param.last_detections
    frame_w, frame_h = param.frame_size

    for det in detections:
        label = det.get_label()
        if label != "person":
            continue

        bbox = det.get_bbox()
        track = det.get_objects_typed(hailo.HAILO_UNIQUE_ID)
        if not track:
            continue
        track_id = track[0].get_id()

        x1 = int(bbox.xmin() * frame_w)
        y1 = int(bbox.ymin() * frame_h)
        x2 = int(bbox.xmax() * frame_w)
        y2 = int(bbox.ymax() * frame_h)

        if x1 <= x <= x2 and y1 <= y <= y2:
            param.locked_track_id = track_id
            print(f"🖱️ Manually locked to Track ID: {track_id}")
            return

# -----------------------------------------------------------------------------------------------
# Callback function
# -----------------------------------------------------------------------------------------------
def app_callback(pad, info, user_data):
    buffer = info.get_buffer()
    if buffer is None:
        return Gst.PadProbeReturn.OK

    user_data.increment()
    format, width, height = get_caps_from_pad(pad)
    user_data.frame_size = (width, height)

    frame = None
    if user_data.use_frame and format and width and height:
        frame = get_numpy_from_buffer(buffer, format, width, height)

    roi = hailo.get_roi_from_buffer(buffer)
    detections = roi.get_objects_typed(hailo.HAILO_DETECTION)

    user_data.last_detections = detections
    locked_bbox = None
    detection_count = 0

    for detection in detections:
        label = detection.get_label()
        bbox = detection.get_bbox()
        confidence = detection.get_confidence()

        track = detection.get_objects_typed(hailo.HAILO_UNIQUE_ID)
        if not track:
            continue
        track_id = track[0].get_id()

        if label == "person":
            if user_data.locked_track_id is None:
                user_data.locked_track_id = track_id
                print(f"🎯 Auto-locked onto Track ID: {track_id}")

            if track_id == user_data.locked_track_id:
                locked_bbox = bbox

            detection_count += 1

    if locked_bbox:
        x1, y1, x2, y2 = locked_bbox.xmin(), locked_bbox.ymin(), locked_bbox.xmax(), locked_bbox.ymax()
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2
        frame_w, frame_h = user_data.frame_size

        error_x = (center_x * frame_w - frame_w / 2) / frame_w
        error_y = (center_y * frame_h - frame_h / 2) / frame_h

        print(f"🔒 Tracking Track ID: {user_data.locked_track_id} | Center: ({center_x:.2f}, {center_y:.2f}) | Frame Size: {user_data.frame_size}")
        print(f"🎯 Target offset: x={error_x:.3f}, y={error_y:.3f}")

        threshold = 0.01
        if abs(error_x) < threshold and abs(error_y) < threshold:
            print("🟢 Target is centered, no movement needed.")
            move_camera_horizontal = "center"
            move_camera_vertical = "center"
        else:
            move_camera_horizontal = "left" if error_x > threshold else "right" if error_x < -threshold else "center"
            move_camera_vertical = "down" if error_y > threshold else "up" if error_y < -threshold else "center"

        print(f"🔧 Move camera: Horizontal: {move_camera_horizontal}, Vertical: {move_camera_vertical}")

        if user_data.use_frame and frame is not None:
            x1_pix = int(x1 * frame_w)
            y1_pix = int(y1 * frame_h)
            x2_pix = int(x2 * frame_w)
            y2_pix = int(y2 * frame_h)
            cx = int(center_x * frame_w)
            cy = int(center_y * frame_h)
            cv2.rectangle(frame, (x1_pix, y1_pix), (x2_pix, y2_pix), (255, 0, 255), 2)
            cv2.line(frame, (frame_w // 2, frame_h // 2), (cx, cy), (255, 0, 255), 2)

    if user_data.use_frame and frame is not None:
        cv2.putText(frame, f"Detections: {detection_count}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(frame, f"{user_data.new_function()} {user_data.new_variable}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        user_data.last_frame = frame.copy()
        user_data.set_frame(frame)

    return Gst.PadProbeReturn.OK

# -----------------------------------------------------------------------------------------------
# Frame Display Thread
# -----------------------------------------------------------------------------------------------
def show_loop(user_data):
    while True:
        if user_data.use_frame and user_data.last_frame is not None:
            cv2.imshow("tracking", user_data.last_frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    cv2.destroyAllWindows()

# -----------------------------------------------------------------------------------------------
if __name__ == "__main__":
    user_data = user_app_callback_class()
    cv2.namedWindow("tracking")
    cv2.setMouseCallback("tracking", on_mouse_click, user_data)

    t = Thread(target=show_loop, args=(user_data,), daemon=True)
    t.start()

    app = GStreamerDetectionApp(app_callback, user_data)
    app.run()
