#!/usr/bin/env python3
"""
Unified ROV Control System
Integrates: Thruster control, Claw control, Sensor receiving, WebSocket broadcasting
"""

import asyncio
import json
import socket
import websockets
import pygame
from pygame.locals import *
import time

# ============================================================================
# CONFIGURATION
# ============================================================================
ARDUINO_IP = "192.168.1.151"
ARDUINO_PORT = 8888
WEBSOCKET_PORT = 8765

# Thruster settings
MAX_POWER = 0.3
THRUSTER_MAPPING = [
    {"name": "OFR", "index": 6},
    {"name": "OFL", "index": 4},
    {"name": "OBR", "index": 2},
    {"name": "OBL", "index": 3},
    {"name": "IFL", "index": 5},
    {"name": "IBL", "index": 0},
    {"name": "IBR", "index": 1},
    {"name": "IFR", "index": 7},
]
THRUSTER_MAPPING = sorted(THRUSTER_MAPPING, key=lambda x: x["index"])

# Claw settings
CLAW_INCREMENT = 30

# ============================================================================
# GLOBAL STATE
# ============================================================================
running = True
connected_clients = set()

# Claw state tracking
claw_state = {
    "angleClaw1": 0,
    "angleClaw1Rot": 0,
    "angleClaw2": 0,
    "angleClaw2Rot": 0,
}

# ============================================================================
# SOCKET INITIALIZATION
# ============================================================================
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("", ARDUINO_PORT))
sock.settimeout(0.1)
print(f"UDP Socket listening on port {ARDUINO_PORT}")

# ============================================================================
# PYGAME/JOYSTICK INITIALIZATION
# ============================================================================
pygame.init()
pygame.joystick.init()

joystick_present = pygame.joystick.get_count() > 0
if joystick_present:
    joystick = pygame.joystick.Joystick(0)
    joystick.init()
    print(f"Joystick connected: {joystick.get_name()}")
    print(f"  Axes: {joystick.get_numaxes()}")
    print(f"  Buttons: {joystick.get_numbuttons()}")
else:
    print("WARNING: No joystick detected. Control disabled.")

# ============================================================================
# THRUSTER FUNCTIONS
# ============================================================================
def map_thruster(value, max_power):
    """Convert -1 to 1 range to PWM microseconds (1100-1900)"""
    return int((value * max_power) * 400 + 1500)


def parse_thruster_control(control_data):
    """Calculate thruster values from control inputs"""
    # XY plane thrusters (horizontal movement)
    xythrusters = {
        "OFR": control_data["surge"] - control_data["yaw"] - control_data["sway"],
        "OFL": -1 * (control_data["surge"] + control_data["yaw"] + control_data["sway"]),
        "OBR": control_data["surge"] - control_data["yaw"] + control_data["sway"],
        "OBL": -1 * (control_data["surge"] + control_data["yaw"] - control_data["sway"]),
    }
    
    # Z plane thrusters (vertical movement)
    zthrusters = {
        "IFL": control_data["heave"] - control_data["roll"] + control_data["pitch"],
        "IBL": -1 * (control_data["heave"] - control_data["roll"] - control_data["pitch"]),
        "IBR": control_data["heave"] + control_data["roll"] - control_data["pitch"],
        "IFR": -1 * control_data["heave"] + control_data["roll"] + control_data["pitch"],
    }
    
    # Normalize XY thrusters
    max_xy = max(abs(v) for v in xythrusters.values()) if xythrusters else 1
    if max_xy > 1:
        for k in xythrusters:
            xythrusters[k] /= max_xy
    
    # Normalize Z thrusters
    max_z = max(abs(v) for v in zthrusters.values()) if zthrusters else 1
    if max_z > 1:
        for k in zthrusters:
            zthrusters[k] /= max_z
    
    # Combine and create command string
    combined = {**xythrusters, **zthrusters}
    control_array = [combined[item["name"]] for item in THRUSTER_MAPPING]
    
    control_string = "c"
    for val in control_array:
        control_string += "," + str(map_thruster(val, MAX_POWER))
    control_string += ",0,0"
    
    return control_string


# ============================================================================
# CLAW FUNCTIONS
# ============================================================================
def send_claw_command(command):
    """Send claw command via UDP"""
    try:
        sock.sendto(command.encode(), (ARDUINO_IP, ARDUINO_PORT))
        print(f"Claw command sent: {command}")
    except Exception as e:
        print(f"Error sending claw command: {e}")


def handle_claw_button(button, state):
    """Handle claw control button presses"""
    global claw_state
    
    # Claw 1 controls (face buttons)
    if button == 3 and state["angleClaw1"] != 180:  # Triangle - Open claw1
        send_claw_command("oc1")
        state["angleClaw1"] += CLAW_INCREMENT
        print(f"Claw1 open: angle {state['angleClaw1']}")
        broadcast_claw_state(state)
        
    elif button == 0 and state["angleClaw1"] != 0:  # X - Close claw1
        send_claw_command("cc1")
        state["angleClaw1"] -= CLAW_INCREMENT
        print(f"Claw1 close: angle {state['angleClaw1']}")
        broadcast_claw_state(state)
        
    elif button == 2 and state["angleClaw1Rot"] != 180:  # Square - Rotate claw1
        send_claw_command("rc1")
        state["angleClaw1Rot"] += CLAW_INCREMENT
        print(f"Claw1 rotate: angle {state['angleClaw1Rot']}")
        broadcast_claw_state(state)
        
    elif button == 1 and state["angleClaw1Rot"] != 0:  # Circle - Unrotate claw1
        send_claw_command("urc1")
        state["angleClaw1Rot"] -= CLAW_INCREMENT
        print(f"Claw1 unrotate: angle {state['angleClaw1Rot']}")
        broadcast_claw_state(state)
    
    # Claw 2 controls (D-pad)
    elif button == 11 and state["angleClaw2"] != 180:  # Up arrow - Open claw2
        send_claw_command("oc2")
        state["angleClaw2"] += CLAW_INCREMENT
        print(f"Claw2 open: angle {state['angleClaw2']}")
        broadcast_claw_state(state)
        
    elif button == 12 and state["angleClaw2"] != 0:  # Down arrow - Close claw2
        send_claw_command("cc2")
        state["angleClaw2"] -= CLAW_INCREMENT
        print(f"Claw2 close: angle {state['angleClaw2']}")
        broadcast_claw_state(state)
        
    elif button == 13 and state["angleClaw2Rot"] != 180:  # Left arrow - Rotate claw2
        send_claw_command("rc2")
        state["angleClaw2Rot"] += CLAW_INCREMENT
        print(f"Claw2 rotate: angle {state['angleClaw2Rot']}")
        broadcast_claw_state(state)
        
    elif button == 14 and state["angleClaw2Rot"] != 0:  # Right arrow - Unrotate claw2
        send_claw_command("urc2")
        state["angleClaw2Rot"] -= CLAW_INCREMENT
        print(f"Claw2 unrotate: angle {state['angleClaw2Rot']}")
        broadcast_claw_state(state)


def broadcast_claw_state(state):
    """Broadcast claw state to all WebSocket clients"""
    payload = {
        "type": "claw_state",
        "claw1_angle": state["angleClaw1"],
        "claw1_rotation": state["angleClaw1Rot"],
        "claw2_angle": state["angleClaw2"],
        "claw2_rotation": state["angleClaw2Rot"],
    }
    asyncio.create_task(broadcast_to_clients(payload))


# ============================================================================
# JOYSTICK CONTROL TASK
# ============================================================================
async def handle_joystick():
    """Main joystick handling loop - controls both thrusters and claws"""
    if not joystick_present:
        print("Joystick task skipped - no joystick detected")
        return
    
    CTRL_DEADZONES = [0.1] * joystick.get_numaxes()
    
    print("Joystick control task started")
    print("  Face buttons (Triangle/X/Square/Circle) control Claw 1")
    print("  D-pad (Up/Down/Left/Right) control Claw 2")
    print("  Left stick controls surge/yaw")
    print("  Right stick controls sway/heave")
    print("  Hold X button for roll/pitch mode")
    
    while running:
        # Process all pygame events
        for event in pygame.event.get():
            if event.type == QUIT:
                print("Quit event received")
                return
            
            elif event.type == JOYBUTTONDOWN:
                # Handle claw controls
                handle_claw_button(event.button, claw_state)
        
        # Read all axes
        axes = [joystick.get_axis(i) for i in range(joystick.get_numaxes())]
        buttons = [joystick.get_button(i) for i in range(joystick.get_numbuttons())]
        
        # Apply deadzones
        for i in range(len(axes)):
            if abs(axes[i]) < CTRL_DEADZONES[i]:
                axes[i] = 0.0
            axes[i] = round(axes[i], 2)
        
        # Calculate thruster control based on joystick input
        # Ensure we have enough axes
        if len(axes) >= 4:
            sway = -axes[2] if len(axes) > 2 else 0  # Right stick left/right
            heave = -axes[3] if len(axes) > 3 else 0  # Right stick up/down
            
            # Check if X button (button 0) is pressed for roll/pitch mode
            if len(buttons) > 0 and buttons[0] == 0:  # X button not pressed
                surge = axes[1] if len(axes) > 1 else 0  # Left stick up/down
                yaw = -axes[0] if len(axes) > 0 else 0   # Left stick left/right
                roll = 0
                pitch = 0
            else:  # X button pressed - roll/pitch mode
                surge = 0
                yaw = 0
                roll = -axes[0] if len(axes) > 0 else 0
                pitch = axes[1] if len(axes) > 1 else 0
        else:
            # Not enough axes, use defaults
            surge = sway = heave = yaw = roll = pitch = 0
        
        # Create control data
        control_data = {
            "surge": surge,
            "sway": sway,
            "heave": heave,
            "yaw": yaw,
            "roll": roll,
            "pitch": pitch,
        }
        
        # Generate and send thruster command
        command = parse_thruster_control(control_data)
        
        try:
            sock.sendto(command.encode(), (ARDUINO_IP, ARDUINO_PORT))
            # Only print if there's actual movement (not all neutral)
            if any(abs(v) > 0.01 for v in control_data.values()):
                print(f"Thrusters: {command[:50]}...")  # Truncate for readability
        except Exception as e:
            print(f"Error sending thruster command: {e}")
        
        await asyncio.sleep(0.05)  # 20Hz control rate


# ============================================================================
# SENSOR RECEIVING TASK
# ============================================================================
async def receive_sensors():
    """Receive sensor data from Arduino via UDP and broadcast to WebSocket clients"""
    print("Sensor receiver task started")
    
    while running:
        try:
            data, addr = sock.recvfrom(1024)
            msg = data.decode().strip()
            print(f"Received from {addr}: {msg}")
            
            payload = None
            
            # Parse humidity data
            if msg.startswith("HUM:"):
                try:
                    humidity = float(msg[4:])
                    payload = {
                        "type": "sensor",
                        "humidity": humidity
                    }
                    print(f"  → Humidity = {humidity}%")
                except ValueError:
                    print(f"  → Bad humidity format: {msg}")
            
            # Parse current data
            elif msg.startswith("CUR:"):
                try:
                    current = float(msg[4:])
                    payload = {
                        "type": "sensor",
                        "current": current
                    }
                    print(f"  → Current = {current}A")
                except ValueError:
                    print(f"  → Bad current format: {msg}")
            
            # Broadcast to WebSocket clients
            if payload:
                await broadcast_to_clients(payload)
        
        except socket.timeout:
            # No data received, continue
            pass
        except Exception as e:
            print(f"Error receiving sensor data: {e}")
        
        await asyncio.sleep(0.02)  # 50Hz polling rate


# ============================================================================
# WEBSOCKET SERVER
# ============================================================================
async def broadcast_to_clients(payload):
    """Broadcast data to all connected WebSocket clients"""
    if not connected_clients:
        return
    
    json_msg = json.dumps(payload)
    dead_clients = []
    
    for client in connected_clients:
        try:
            await client.send(json_msg)
        except Exception as e:
            print(f"Error sending to client: {e}")
            dead_clients.append(client)
    
    # Remove dead connections
    for client in dead_clients:
        connected_clients.discard(client)


async def websocket_handler(websocket):
    """Handle WebSocket client connections"""
    connected_clients.add(websocket)
    client_addr = websocket.remote_address
    print(f"WebSocket client connected from {client_addr} ({len(connected_clients)} total)")
    
    try:
        # Send initial claw state
        initial_state = {
            "type": "claw_state",
            "claw1_angle": claw_state["angleClaw1"],
            "claw1_rotation": claw_state["angleClaw1Rot"],
            "claw2_angle": claw_state["angleClaw2"],
            "claw2_rotation": claw_state["angleClaw2Rot"],
        }
        await websocket.send(json.dumps(initial_state))
        
        # Keep connection alive
        async for message in websocket:
            # Echo or handle client messages if needed
            print(f"Received from client: {message}")
    
    except websockets.ConnectionClosed:
        print(f"WebSocket client {client_addr} disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        connected_clients.discard(websocket)
        print(f"Client {client_addr} removed ({len(connected_clients)} remaining)")


# ============================================================================
# MAIN FUNCTION
# ============================================================================
async def main():
    """Main entry point - start all tasks"""
    print("=" * 60)
    print("UNIFIED ROV CONTROL SYSTEM")
    print("=" * 60)
    print(f"Arduino IP: {ARDUINO_IP}:{ARDUINO_PORT}")
    print(f"WebSocket Server: ws://0.0.0.0:{WEBSOCKET_PORT}")
    print("=" * 60)
    
    # Start WebSocket server
    async with websockets.serve(websocket_handler, "0.0.0.0", WEBSOCKET_PORT):
        print("WebSocket server started")
        
        # Run all tasks concurrently
        try:
            await asyncio.gather(
                handle_joystick(),
                receive_sensors()
            )
        except KeyboardInterrupt:
            print("\nShutdown signal received")
        finally:
            print("Cleaning up...")
            pygame.quit()
            sock.close()
            print("Goodbye!")


# ============================================================================
# ENTRY POINT
# ============================================================================
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting...")