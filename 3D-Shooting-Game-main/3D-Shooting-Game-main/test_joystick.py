"""
Diagnostic tool to test whether your Joystick or Arduino is detected by your PC.
Run this from your terminal:
    python test_joystick.py
"""

import sys
import time
import pygame as pg

try:
    import serial
    import serial.tools.list_ports
    HAS_SERIAL = True
except ImportError:
    HAS_SERIAL = False

print("=" * 60)
print("       JOYSTICK & CONTROLLER DIAGNOSTIC TOOL")
print("=" * 60)

# 1. Check COM Ports (Arduino)
print("\n[1] Checking COM Ports for Arduino...")
if not HAS_SERIAL:
    print("   WARNING: 'pyserial' is not installed. Run: pip install pyserial")
else:
    all_ports = list(serial.tools.list_ports.comports())
    
    # Priority: Bluetooth COM19 (Gift)
    bt_port = None
    arduino_ports = []
    other_ports = []

    for p in all_ports:
        desc = (p.description or '').lower()
        if p.device.upper() == 'COM19' or 'gift' in desc or 'serialport' in desc:
            bt_port = p
        elif 'arduino' in desc or '2341:' in (p.hwid or '').lower():
            arduino_ports.append(p)
        elif not any(k in desc for k in ['bluetooth', 'bthenum', 'bth']) and p.device.upper() not in ['COM18', 'COM19']:
            other_ports.append(p)

    target_port = None
    target_baud = 9600

    if bt_port:
        target_port = bt_port
        target_baud = 9600
        print(f"   -> FOUND BLUETOOTH HC-05! Port: {target_port.device} ({target_port.description})")
    elif arduino_ports:
        target_port = arduino_ports[0]
        target_baud = 115200
        print(f"   -> FOUND USB ARDUINO! Port: {target_port.device} ({target_port.description})")
    elif other_ports:
        target_port = other_ports[0]
        target_baud = 115200
        print(f"   -> Found USB-Serial device: {target_port.device} ({target_port.description})")
    else:
        print("   -> No device found! Check your Bluetooth pairing or USB connection.")

    if target_port:
        port_name = target_port.device
        print(f"\n   Connecting to {port_name} at {target_baud} baud...")
        try:
            ser = serial.Serial(port_name, target_baud, timeout=2.0)
            ser.reset_input_buffer()
            print(f"   SUCCESS: Connected to {port_name}!")
            print("   Streaming live data... Move your sticks or press buttons! (Press Ctrl+C to stop)")
            data_count = 0
            try:
                while True:
                    line = ser.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        data_count += 1
                        print(f"\r   [{data_count:04d}] {line}               ", end="", flush=True)
            except KeyboardInterrupt:
                print(f"\n\n   Live test stopped. Received {data_count} data packets.")
            ser.close()
        except Exception as e:
            print(f"\n   ERROR opening {port_name}: {e}")
            print("   -> If the Arduino IDE 'Serial Monitor' is open, CLOSE IT! Windows only allows one program to use the COM port at a time.")

# 2. Check Pygame Joysticks (USB Gamepads)
print("\n[2] Checking for USB Gamepads / Controllers via Pygame...")
pg.init()
pg.joystick.init()
joy_count = pg.joystick.get_count()

if joy_count == 0:
    print("   -> No standard USB Gamepads detected.")
    print("      (Since your controller is an Arduino Uno on COM16, it communicates via Serial, which is fully supported!)")
else:
    print(f"   -> Found {joy_count} game controller(s):")
    for i in range(joy_count):
        joy = pg.joystick.Joystick(i)
        joy.init()
        print(f"      Controller #{i}: {joy.get_name()}")

print("\n" + "=" * 60)
print("Diagnostic finished.")
print("=" * 60)
