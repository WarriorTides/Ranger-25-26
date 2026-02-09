#!/bin/bash

# ROV Pi Startup Script
# This script launches both the control system and camera server on the Raspberry Pi

echo "╔════════════════════════════════════════════════════════╗"
echo "║         ROV RASPBERRY PI STARTUP SCRIPT               ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

# Check if running on Pi or Linux
if [ ! -f /proc/cpuinfo ] || ! grep -q "Raspberry Pi\|BCM" /proc/cpuinfo 2>/dev/null; then
    echo "⚠️  WARNING: This doesn't appear to be a Raspberry Pi"
    echo "   This script is designed for the Pi, but will continue anyway..."
    echo ""
fi

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed!"
    echo "   Install with: sudo apt install python3"
    exit 1
fi

echo "What would you like to start?"
echo ""
echo "  1) Control System only (thrusters, claws, sensors)"
echo "  2) Camera Server only (3 camera streams)"
echo "  3) Both Control System + Camera Server (RECOMMENDED)"
echo "  4) Test system components"
echo "  5) Exit"
echo ""
read -p "Enter choice [1-5]: " choice

case $choice in
    1)
        echo ""
        echo "🚀 Starting ROV Control System..."
        echo "   Thrusters, Claws, and Sensor monitoring"
        echo "   Press Ctrl+C to stop"
        echo ""
        python3 unified_rov_control.py
        ;;
    
    2)
        echo ""
        echo "🎥 Starting Camera Server..."
        echo "   Streaming 3 cameras via UDP"
        echo "   Press Ctrl+C to stop"
        echo ""
        python3 camera_server.py
        ;;
    
    3)
        echo ""
        echo "🚀 Starting BOTH systems..."
        echo ""
        echo "This will run:"
        echo "  - Control System (thrusters, claws, sensors)"
        echo "  - Camera Server (3 camera streams)"
        echo ""
        echo "Press Ctrl+C to stop both"
        echo ""
        
        # Create a trap to kill both processes on Ctrl+C
        trap 'echo ""; echo "Stopping all processes..."; kill $PID1 $PID2 2>/dev/null; exit' INT
        
        # Start control system in background
        echo "Starting Control System..."
        python3 unified_rov_control.py &
        PID1=$!
        sleep 2
        
        # Start camera server in background
        echo "Starting Camera Server..."
        python3 camera_server.py &
        PID2=$!
        sleep 2
        
        echo ""
        echo "═══════════════════════════════════════════════════════"
        echo "✅ BOTH SYSTEMS RUNNING"
        echo "═══════════════════════════════════════════════════════"
        echo "Control System PID: $PID1"
        echo "Camera Server PID:  $PID2"
        echo ""
        echo "Monitoring output below..."
        echo "Press Ctrl+C to stop everything"
        echo "═══════════════════════════════════════════════════════"
        echo ""
        
        # Wait for both processes
        wait $PID1 $PID2
        ;;
    
    4)
        echo ""
        echo "🧪 Running system tests..."
        echo ""
        python3 test_system.py
        ;;
    
    5)
        echo "Exiting..."
        exit 0
        ;;
    
    *)
        echo "Invalid choice. Exiting..."
        exit 1
        ;;
esac

echo ""
echo "✅ Shutdown complete"