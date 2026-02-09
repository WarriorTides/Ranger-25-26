#!/usr/bin/env python3
"""
ROV Camera Server
Captures from 3 cameras and streams to PC via UDP
Run this on the Raspberry Pi alongside unified_rov_control.py
"""

import cv2
import socket
import json
import base64
import time
import threading

# ============================================================================
# CONFIGURATION
# ============================================================================
PC_IP = "192.168.1.119"  # IP of computer running the GUI
CAMERA_PORTS = [5005, 5006, 5007]  # UDP ports for each camera

# Camera device indices (adjust these based on your setup)
# Use: ls /dev/video* to see available cameras on Linux
CAMERA_INDICES = [0, 4, 3]  # Device indices for cam1, cam2, cam3

# Camera settings
FRAME_WIDTH = 320
FRAME_HEIGHT = 240
CAMERA_FPS = 15
JPEG_QUALITY = 70  # 0-100, lower = smaller file size

# ============================================================================
# SOCKET INITIALIZATION
# ============================================================================
sockets = [socket.socket(socket.AF_INET, socket.SOCK_DGRAM) for _ in CAMERA_PORTS]
print(f"Created {len(sockets)} UDP sockets")

# ============================================================================
# CAMERA INITIALIZATION
# ============================================================================
caps = []

print("Initializing cameras...")
for i, cam_idx in enumerate(CAMERA_INDICES):
    print(f"  Opening camera {cam_idx} (ID {i+1})...")
    cap = cv2.VideoCapture(cam_idx)
    
    if not cap.isOpened():
        print(f"    ⚠️  WARNING: Could not open camera {cam_idx}")
        cap = None
    else:
        # Configure camera
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
        cap.set(cv2.CAP_PROP_FPS, CAMERA_FPS)
        
        # Verify settings
        actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = cap.get(cv2.CAP_PROP_FPS)
        
        print(f"    ✅ Camera {cam_idx} initialized: {actual_w}x{actual_h} @ {actual_fps}fps")
    
    caps.append(cap)
    time.sleep(0.5)  # Give camera time to initialize

# Count working cameras
working_cameras = sum(1 for cap in caps if cap is not None and cap.isOpened())
print(f"\n✅ {working_cameras}/{len(CAMERA_INDICES)} cameras ready")

# ============================================================================
# FRAME SENDING FUNCTION
# ============================================================================
def send_frame(cam_idx, frame):
    """Encode frame as JPEG and send via UDP"""
    try:
        # Encode frame to JPEG
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
        
        # Convert to base64
        jpg_as_text = base64.b64encode(buffer).decode('utf-8')
        
        # Create JSON message
        msg = json.dumps({
            "type": "camera",
            "camera_id": cam_idx + 1,
            "data": jpg_as_text,
            "timestamp": time.time()
        }).encode('utf-8')
        
        # Send via UDP
        sockets[cam_idx].sendto(msg, (PC_IP, CAMERA_PORTS[cam_idx]))
        
        return True
    except Exception as e:
        print(f"Error sending frame from camera {cam_idx}: {e}")
        return False


# ============================================================================
# CAMERA LOOP (runs in separate thread for each camera)
# ============================================================================
def camera_loop(cam_idx, cap):
    """Main loop for each camera - captures and sends frames"""
    # Stagger start times to avoid all cameras grabbing at once
    time.sleep(cam_idx * 0.05)
    
    if cap is None or not cap.isOpened():
        print(f"❌ Camera {CAMERA_INDICES[cam_idx]} (ID {cam_idx + 1}) thread exiting - camera not available")
        return
    
    frame_count = 0
    error_count = 0
    last_status_time = time.time()
    
    print(f"🎥 Camera {CAMERA_INDICES[cam_idx]} (ID {cam_idx + 1}) streaming started")
    
    while True:
        try:
            # Check if camera is still open
            if not cap.isOpened():
                print(f"❌ Camera {CAMERA_INDICES[cam_idx]} (ID {cam_idx + 1}) lost connection")
                break
            
            # Read frame
            ret, frame = cap.read()
            
            if ret and frame is not None:
                # Send frame
                if send_frame(cam_idx, frame):
                    frame_count += 1
                    error_count = 0  # Reset error count on success
                else:
                    error_count += 1
                
                # Status update every 5 seconds
                current_time = time.time()
                if current_time - last_status_time >= 5.0:
                    fps = frame_count / (current_time - last_status_time + 0.001)
                    print(f"📊 Camera {cam_idx + 1}: {frame_count} frames ({fps:.1f} fps)")
                    frame_count = 0
                    last_status_time = current_time
            else:
                error_count += 1
                if error_count % 30 == 0:  # Print every 30 errors
                    print(f"⚠️  Camera {CAMERA_INDICES[cam_idx]} (ID {cam_idx + 1}) failed to read frame (error #{error_count})")
            
            # Exit if too many consecutive errors
            if error_count > 100:
                print(f"❌ Camera {CAMERA_INDICES[cam_idx]} (ID {cam_idx + 1}) too many errors, stopping")
                break
            
            # Control frame rate (~15 fps = ~66ms per frame)
            time.sleep(0.066)
        
        except Exception as e:
            print(f"❌ Camera {CAMERA_INDICES[cam_idx]} (ID {cam_idx + 1}) error: {e}")
            error_count += 1
            time.sleep(0.1)


# ============================================================================
# START CAMERA THREADS
# ============================================================================
threads = []

for idx, cap in enumerate(caps):
    t = threading.Thread(target=camera_loop, args=(idx, cap), name=f"Camera-{idx+1}")
    t.daemon = True  # Thread will exit when main program exits
    t.start()
    threads.append(t)

print("\n" + "=" * 60)
print("🎥 CAMERA STREAMING STARTED")
print("=" * 60)
print(f"Streaming to: {PC_IP}")
print(f"Ports: {CAMERA_PORTS}")
print(f"Active cameras: {working_cameras}")
print("Press Ctrl+C to stop")
print("=" * 60 + "\n")

# ============================================================================
# MAIN LOOP - Keep alive
# ============================================================================
try:
    while True:
        # Check thread health
        alive_threads = sum(1 for t in threads if t.is_alive())
        if alive_threads == 0:
            print("⚠️  All camera threads have stopped!")
            break
        
        time.sleep(1)

except KeyboardInterrupt:
    print("\n\n🛑 Shutdown signal received...")

finally:
    print("Cleaning up...")
    
    # Release cameras
    for idx, cap in enumerate(caps):
        if cap is not None and cap.isOpened():
            cap.release()
            print(f"  Camera {idx + 1} released")
    
    # Close sockets
    for idx, sock in enumerate(sockets):
        sock.close()
        print(f"  Socket {idx + 1} closed")
    
    print("\n✅ Camera server shut down cleanly")
    print("Goodbye!\n")