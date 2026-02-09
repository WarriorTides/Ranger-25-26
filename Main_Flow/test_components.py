#!/usr/bin/env python3
"""
ROV Component Test Script
Tests each component of the integrated system independently
"""

import sys
import time


def test_joystick():
    """Test if joystick is detected"""
    print("\n" + "="*50)
    print("TESTING JOYSTICK")
    print("="*50)

    try:
        import pygame
        pygame.init()
        pygame.joystick.init()

        count = pygame.joystick.get_count()
        print(f"Joysticks detected: {count}")

        if count > 0:
            joystick = pygame.joystick.Joystick(0)
            joystick.init()
            print(f"✓ Joystick name: {joystick.get_name()}")
            print(f"✓ Axes: {joystick.get_numaxes()}")
            print(f"✓ Buttons: {joystick.get_numbuttons()}")
            return True
        else:
            print("✗ No joystick detected!")
            return False

    except Exception as e:
        print(f"✗ Error: {e}")
        return False
    finally:
        pygame.quit()


def test_control_thread():
    """Test if control thread can start"""
    print("\n" + "="*50)
    print("TESTING CONTROL THREAD")
    print("="*50)

    try:
        from control_thread import ControlThread

        print("Creating control thread...")
        thread = ControlThread(arduino_ip="192.168.1.151", arduino_port=8888)

        print("Starting control thread...")
        thread.start()

        print("Letting it run for 3 seconds...")
        time.sleep(3)

        print("Stopping control thread...")
        thread.stop()
        thread.join(timeout=2)

        print("✓ Control thread works!")
        return True

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_sensor_websocket():
    """Test if sensor websocket server can start"""
    print("\n" + "="*50)
    print("TESTING SENSOR WEBSOCKET SERVER")
    print("="*50)

    try:
        from sensor_websocket_thread import SensorWebSocketThread

        print("Creating sensor WebSocket thread...")
        thread = SensorWebSocketThread(ws_port=8765, udp_port=8888)

        print("Starting sensor WebSocket thread...")
        thread.start()

        print("Letting it run for 3 seconds...")
        time.sleep(3)

        print("Stopping sensor WebSocket thread...")
        thread.stop()
        thread.join(timeout=2)

        print("✓ Sensor WebSocket server works!")
        return True

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_imports():
    """Test if all required modules can be imported"""
    print("\n" + "="*50)
    print("TESTING IMPORTS")
    print("="*50)

    required = [
        ("PyQt6", "PyQt6"),
        ("pygame", "pygame"),
        ("cv2", "opencv-python"),
        ("numpy", "numpy"),
        ("websockets", "websockets"),
    ]

    all_good = True

    for module, package in required:
        try:
            __import__(module)
            print(f"✓ {module} ({package})")
        except ImportError:
            print(f"✗ {module} ({package}) - NOT INSTALLED")
            all_good = False

    return all_good


def test_files_exist():
    """Test if all required files exist"""
    print("\n" + "="*50)
    print("TESTING FILE EXISTENCE")
    print("="*50)

    import os

    required_files = [
        "main_rov.py",
        "control_thread.py",
        "sensor_websocket_thread.py",
        "CamReceiver.py",
        "SensorClient_Dummy.py",
        "Cam_Recorder.py",
    ]

    all_good = True

    for filename in required_files:
        if os.path.exists(filename):
            print(f"✓ {filename}")
        else:
            print(f"✗ {filename} - MISSING")
            all_good = False

    return all_good


def main():
    print("\n" + "="*60)
    print(" ROV SYSTEM COMPONENT TEST")
    print("="*60)

    results = {}

    # Test imports first
    results['imports'] = test_imports()

    # Test file existence
    results['files'] = test_files_exist()

    # Only test components if basic requirements are met
    if results['imports'] and results['files']:
        results['joystick'] = test_joystick()
        results['control'] = test_control_thread()
        results['sensor_ws'] = test_sensor_websocket()
    else:
        print("\n⚠️  Skipping component tests due to missing requirements")
        results['joystick'] = False
        results['control'] = False
        results['sensor_ws'] = False

    # Summary
    print("\n" + "="*60)
    print(" TEST SUMMARY")
    print("="*60)

    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")

    all_passed = all(results.values())

    print("\n" + "="*60)
    if all_passed:
        print("✓ ALL TESTS PASSED - System ready to run!")
    else:
        print("✗ SOME TESTS FAILED - Fix issues before running")
    print("="*60 + "\n")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
