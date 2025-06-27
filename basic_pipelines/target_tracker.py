import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
import os
import numpy as np
import cv2
import hailo
import serial  # 🔧 If you're using serial to talk to the drone

import asyncio
import websockets
import threading

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
        self.locked_track_id = None  # 🔧 Track ID to follow
        self.frame_size = (640, 480)  # default fallback

    def new_function(self):
        return "The meaning of life is: "
    
class UserDataServer:
    def __init__(self, user_data):
        self.user_data = user_data

    async def handler(self, websocket, path):
        print(f"🔌 Client connected: {websocket.remote_address}")
        async for message in websocket:
            print(f"📥 Received: {message}")
            if message.startswith("SET_ID "):
                try:
                    track_id = int(message.split()[1])
                    self.user_data.locked_track_id = track_id
                    await websocket.send(f"✅ Locked on ID {track_id}")
                    print(f"✅ Locked on ID {track_id}")
                except Exception as e:
                    await websocket.send(f"❌ Error: {e}")

            elif message.strip() == "STOP":
                self.user_data.locked_track_id = None
                await websocket.send("✅ Stopped tracking")
                print("✅ Stopped tracking")
            else:
                await websocket.send("❓ Unknown command")

    async def start_server(self):
        server = await websockets.serve(self.handler, "localhost", 8765)
        print("🌐 WebSocket server running at ws://localhost:8765")
        await server.wait_closed()



# -----------------------------------------------------------------------------------------------
# Callback function
# -----------------------------------------------------------------------------------------------
def app_callback(pad, info, user_data):
    buffer = info.get_buffer()
    if buffer is None:
        return Gst.PadProbeReturn.OK

    user_data.increment()
    # string_to_print = f"Frame count: {user_data.get_count()}\n"

    format, width, height = get_caps_from_pad(pad)
    user_data.frame_size = (width, height)  # 🔧 Store frame size for normalization

    frame = None
    if user_data.use_frame and format and width and height:
        frame = get_numpy_from_buffer(buffer, format, width, height)

    roi = hailo.get_roi_from_buffer(buffer)
    detections = roi.get_objects_typed(hailo.HAILO_DETECTION)

    locked_bbox = None
    detection_count = 0

    for detection in detections:
        label = detection.get_label()
        bbox = detection.get_bbox()
        confidence = detection.get_confidence()

        track_id = 0
        track = detection.get_objects_typed(hailo.HAILO_UNIQUE_ID)
        if len(track) == 1:
            track_id = track[0].get_id()

        # 🔧 Lock target logic
        # if label == "person":
        #     if user_data.locked_track_id is None:
        #         user_data.locked_track_id = track_id
        #         print(f"🎯 Locked onto Track ID: {track_id}")
            
        #     if track_id == user_data.locked_track_id:
        #         locked_bbox = bbox

        #     detection_count += 1
        
        if label == "person":
            if user_data.locked_track_id == track_id:
                locked_bbox = bbox
            detection_count += 1

    # print(f"Locked Box: {dir(locked_bbox)}, Detection Count: {detection_count}")

    # 🔧 If locked target is found
    if locked_bbox:
        x1, y1, x2, y2 = locked_bbox.xmin(), locked_bbox.ymin(), locked_bbox.xmax(), locked_bbox.ymax()
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2
        frame_w, frame_h = user_data.frame_size

        error_x = center_x - 0.5  # left/right deviation
        error_y = center_y - 0.5  # up/down deviation

        error_x = (center_x * frame_w  - frame_w / 2) / frame_w  # -0.5 to 0.5
        error_y = (center_y * frame_h - frame_h / 2) / frame_h
        
        print(f"🔒 Tracking Track ID: {user_data.locked_track_id}"
              f" | Center: ({center_x:.2f}, {center_y:.2f})"
              f" | Frame Size: {user_data.frame_size}"
              f" | x1={x1:.2f}, y1={y1:.2f}, x2={x2:.2f}, y2={y2:.2f})")
        print(f"🎯 Target offset: x={error_x:.3f}, y={error_y:.3f}\n")

        # Set movement thresholds
        threshold = 0.01

        if abs(error_x) < threshold and abs(error_y) < threshold:
            print("🟢 Target is centered, no movement needed.")
            move_camera_horizontal = "center"
            move_camera_vertical = "center"
        else:
            move_camera_horizontal = (
            "left" if error_x > threshold else "right" if error_x < -threshold else "center"
            )
            move_camera_vertical = (
            "down" if error_y > threshold else "up" if error_y < -threshold else "center"
            )
        
        print(f"🔧 Move camera: "
              f"Horizontal: {move_camera_horizontal}, Verical: {move_camera_vertical}")

        # -x move camera right, +x move camera left
        # -y move camera up, +y move camera down

        # 🔧 Send to drone (serial or UDP)
        # try:
        #     send_to_drone(error_x, error_y)
        # except Exception as e:
        #     print(f"⚠️ Failed to send: {e}")

        if user_data.use_frame and frame is not None:
            # Draw crosshairs
            cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (255, 0, 255), 2)
            cv2.line(frame, (int(frame_w/2), int(frame_h/2)), (int(center_x), int(center_y)), (255, 0, 255), 2)

    if user_data.use_frame and frame is not None:
        cv2.putText(frame, f"Detections: {detection_count}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(frame, f"{user_data.new_function()} {user_data.new_variable}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        user_data.set_frame(frame)

    # print(string_to_print)
    return Gst.PadProbeReturn.OK

# 🔧 DRONE COMMUNICATION LAYER
# Serial or UDP — customize as needed
# Example: serial
# try:
#     ser = serial.Serial("/dev/ttyUSB0", 115200, timeout=1)
# except:
#     ser = None

# def send_to_drone(error_x, error_y):
#     if ser and ser.is_open:
#         msg = f"TRACK,{error_x:.3f},{error_y:.3f}\n"
#         ser.write(msg.encode())
#         print(f"📡 Sent: {msg.strip()}")
#     else:
#         print("❌ Serial not open")

# -----------------------------------------------------------------------------------------------
if __name__ == "__main__":
    user_data = user_app_callback_class()
      # Start WebSocket server in separate thread
    server = UserDataServer(user_data)
    loop = asyncio.new_event_loop()

    def run_ws_server():
        asyncio.set_event_loop(loop)
        loop.run_until_complete(server.start_server())

    threading.Thread(target=run_ws_server, daemon=True).start()


    app = GStreamerDetectionApp(app_callback, user_data)
    app.run()
