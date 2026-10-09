import math
import threading
import pygame as pg

try:
    import serial
    import serial.tools.list_ports
    HAS_SERIAL = True
except ImportError:
    HAS_SERIAL = False


class JoystickController:
    """
    Handles input from both:
    1. Arduino joysticks via USB Serial (pyserial).
    2. Standard USB Gamepads/Controllers via pygame.joystick.
    """
    def __init__(self, game):
        self.game = game

        # Analog values (-1.0 to 1.0)
        self.move_x = 0.0
        self.move_y = 0.0
        self.look_x = 0.0
        self.look_y = 0.0

        # Double-flick UP gesture detection on Right Stick to open Mini-Map
        self.flick_state = 0  # 0: IDLE, 1: FIRST_UP, 2: NEUTRAL, 3: COOLDOWN
        self.flick_first_time = 0

        # Thread-safe button triggers (single press events)
        self.shoot_pressed = False
        self.escape_pressed = False
        self.map_pressed = False
        self.last_raw_shoot = False
        self.last_raw_escape = False
        self.last_raw_map = False

        # State tracking for standard USB gamepads
        self.pad_shoot_prev = False
        self.pad_map_prev = False

        # Deadzone to prevent stick drift
        self.deadzone = 0.15

        # Initialize Pygame joystick subsystem
        self.pg_joysticks = []
        self.init_pygame_joysticks()

        # Serial Arduino connection
        self.serial_port = None
        self.running = True
        self.serial_thread = None

        if HAS_SERIAL:
            self.start_serial_thread()

    def init_pygame_joysticks(self):
        """Initializes standard USB gamepads if plugged in."""
        try:
            if not pg.joystick.get_init():
                pg.joystick.init()
            count = pg.joystick.get_count()
            self.pg_joysticks = []
            for i in range(count):
                joy = pg.joystick.Joystick(i)
                joy.init()
                self.pg_joysticks.append(joy)
                print(f"[JOYSTICK] Detected USB Game Controller: '{joy.get_name()}' ({joy.get_num_axes()} axes, {joy.get_num_buttons()} buttons)")
        except Exception:
            pass

    def start_serial_thread(self):
        """Starts a background thread to read Arduino serial data without blocking the game."""
        self.serial_thread = threading.Thread(target=self._serial_worker, daemon=True)
        self.serial_thread.start()

    def _serial_worker(self):
        """Background worker that detects Arduino and reads joystick data."""
        debug_counter = 0
        while self.running:
            if self.serial_port is None or not self.serial_port.is_open:
                self._find_and_connect_arduino()
                if self.serial_port is None:
                    pg.time.delay(2000)
                    continue

            # 1. Read line from serial port
            try:
                line = self.serial_port.readline().decode('utf-8', errors='ignore').strip()
            except (serial.SerialException, OSError) as e:
                print(f"[JOYSTICK] Serial connection lost ({e}). Searching for device...")
                try:
                    if self.serial_port:
                        self.serial_port.close()
                except Exception:
                    pass
                self.serial_port = None
                pg.time.delay(1000)
                continue

            if not line:
                continue

            # 2. Parse comma-separated joystick values
            try:
                # Clean up any accidental semicolons or spaces
                cleaned = line.replace(';', ',').replace(' ', '')
                parts = cleaned.split(',')
                if len(parts) < 4:
                    continue

                raw_vals = [float(p) for p in parts if p != '']
                if len(raw_vals) < 4:
                    continue

                # Auto-detect format:
                # Format A (Normalized): values are between -1.0 and 1.0
                # Format B (Raw ADC): values are between 0 and 1023 (center ~512)
                mx = raw_vals[0]
                my = raw_vals[1]
                if abs(mx) > 2.0 or abs(my) > 2.0:
                    # Raw 0-1023 ADC
                    mx = (mx - 512.0) / 512.0
                    my = -(my - 512.0) / 512.0 # Invert Y so up is forward
                    lx = (raw_vals[2] - 512.0) / 512.0 if len(raw_vals) > 2 else 0.0
                    ly = -(raw_vals[3] - 512.0) / 512.0 if len(raw_vals) > 4 else 0.0
                    b_escape = int(raw_vals[4]) == 1 if len(raw_vals) > 5 else False
                    b_shoot = int(raw_vals[-1]) == 1
                else:
                    # Normalized -1.0 to 1.0
                    # Format A (6 parts): moveX, moveY, btnLeft (Escape), lookX, lookY, btnRight (Shoot)
                    if len(raw_vals) >= 6:
                        lx = raw_vals[3]
                        ly = raw_vals[4]
                        b_escape = int(raw_vals[2]) == 1
                        b_shoot = int(raw_vals[5]) == 1
                    # Format B (5 parts): moveX, moveY, btnLeft (Escape), lookX, btnRight (Shoot)
                    elif len(raw_vals) == 5:
                        lx = raw_vals[3]
                        ly = 0.0
                        b_escape = int(raw_vals[2]) == 1
                        b_shoot = int(raw_vals[4]) == 1
                    else:
                        # 4 parts: moveX, moveY, lookX, btnShoot
                        lx = raw_vals[2]
                        ly = 0.0
                        b_escape = False
                        b_shoot = int(raw_vals[3]) == 1

                self.move_x = self._apply_deadzone(mx)
                self.move_y = self._apply_deadzone(my)
                self.look_x = self._apply_deadzone(lx)
                self.look_y = self._apply_deadzone(ly)

                # Thread-safe edge trigger detection
                if b_shoot and not self.last_raw_shoot:
                    self.shoot_pressed = True
                    print("[JOYSTICK] >>> RIGHT SWITCH PRESSED -> SHOOT! <<<")
                self.last_raw_shoot = b_shoot

                if b_escape and not self.last_raw_escape:
                    self.escape_pressed = True
                    print("[JOYSTICK] >>> LEFT SWITCH PRESSED -> ESCAPE! <<<")
                self.last_raw_escape = b_escape

                # Print immediately whenever Right Stick Y (Up/Down) moves
                if abs(self.look_y) > 0.15:
                    print(f"[JOYSTICK] Right Stick Y (Up/Down) = {self.look_y:+.2f}")

                # Periodic debug log (first 10 packets, then every ~60 packets when moving or clicking)
                debug_counter += 1
                if debug_counter <= 8 or (debug_counter % 60 == 0 and (abs(self.move_x) > 0.05 or abs(self.look_x) > 0.05 or abs(self.look_y) > 0.05 or b_shoot or b_escape)):
                    print(f"[JOYSTICK] Move: ({self.move_x:+.2f}, {self.move_y:+.2f}) | Look: ({self.look_x:+.2f}, {self.look_y:+.2f}) | Shoot: {b_shoot} | Esc: {b_escape}")

            except (ValueError, IndexError):
                # Ignore partial/malformed line during startup
                continue

    def _find_and_connect_arduino(self):
        """Auto-detects COM port with Bluetooth HC-05 (COM19) or USB Arduino."""
        if not HAS_SERIAL:
            return
        try:
            ports = list(serial.tools.list_ports.comports())
            if not ports:
                return

            # Pass 1: Try Bluetooth Outgoing port (COM19 / Gift) at 9600 baud
            bt_ports = [p for p in ports if p.device.upper() == 'COM19' or 'gift' in (p.description or '').lower() or 'serialport' in (p.description or '').lower()]
            for p in bt_ports:
                try:
                    ser = serial.Serial(p.device, 9600, timeout=1.0)
                    try:
                        ser.reset_input_buffer()
                    except Exception:
                        pass
                    self.serial_port = ser
                    print(f"[JOYSTICK] Successfully connected to WIRELESS BLUETOOTH on {p.device} ({p.description}) at 9600 baud!")
                    return
                except Exception as e:
                    # May take a second to connect over Bluetooth RFCOMM
                    continue

            # Pass 2: USB Arduino (e.g. Arduino Uno on COM14) at 115200 baud
            valid_usb_ports = []
            for p in ports:
                desc = (p.description or '').lower()
                hwid = (p.hwid or '').lower()
                if 'bluetooth' in desc or 'bthenum' in hwid or 'bth' in desc or p.device.upper() in ['COM18', 'COM19']:
                    continue
                valid_usb_ports.append(p)

            for p in valid_usb_ports:
                desc = (p.description or '').lower()
                hwid = (p.hwid or '').lower()
                if 'arduino' in desc or '2341:' in hwid:
                    try:
                        ser = serial.Serial(p.device, 115200, timeout=0.5)
                        try:
                            ser.reset_input_buffer()
                        except Exception:
                            pass
                        self.serial_port = ser
                        print(f"[JOYSTICK] Successfully connected to USB Arduino on {p.device} ({p.description})")
                        return
                    except Exception as e:
                        print(f"[JOYSTICK] Notice: Found {p.device} but could not open it: {e}")
                        print("           -> Make sure no other 'python main.py' is running and Arduino Serial Monitor is closed!")
                        continue

            # Pass 3: USB-Serial adapter chips (CH340, CP2102, FTDI)
            for p in valid_usb_ports:
                desc = (p.description or '').lower()
                if any(k in desc for k in ['ch340', 'usb-serial', 'ftdi', 'cp210', 'usb serial']):
                    try:
                        ser = serial.Serial(p.device, 115200, timeout=0.5)
                        try:
                            ser.reset_input_buffer()
                        except Exception:
                            pass
                        self.serial_port = ser
                        print(f"[JOYSTICK] Connected to Serial Adapter on {p.device} ({p.description})")
                        return
                    except Exception as e:
                        print(f"[JOYSTICK] Notice: Could not open {p.device}: {e}")
                        continue

            # Pass 4: Any remaining non-Bluetooth COM port
            for p in valid_usb_ports:
                try:
                    ser = serial.Serial(p.device, 115200, timeout=0.5)
                    try:
                        ser.reset_input_buffer()
                    except Exception:
                        pass
                    self.serial_port = ser
                    print(f"[JOYSTICK] Connected to {p.device} ({p.description})")
                    return
                except Exception:
                    continue
        except Exception:
            pass

    def _apply_deadzone(self, val):
        if abs(val) < self.deadzone:
            return 0.0
        return val

    def update(self):
        """Update pygame joystick states (if connected) and check for hotplugged controllers."""
        # Hotplug detection: check if a controller was plugged in after the game started
        try:
            current_count = pg.joystick.get_count()
            if current_count != len(self.pg_joysticks):
                self.init_pygame_joysticks()
        except Exception:
            pass

        # Read standard USB gamepad if present
        if self.pg_joysticks:
            try:
                joy = self.pg_joysticks[0]
                num_axes = joy.get_num_axes()
                if num_axes >= 2:
                    self.move_x = self._apply_deadzone(joy.get_axis(0))
                    self.move_y = self._apply_deadzone(-joy.get_axis(1)) # invert Y so up = forward

                # Smart right-stick detection (Axis 2 or Axis 3 depending on Xbox vs DirectInput)
                if num_axes >= 4:
                    ax2 = joy.get_axis(2)
                    ax3 = joy.get_axis(3)
                    self.look_x = self._apply_deadzone(ax2 if abs(ax2) > abs(ax3) else ax3)
                elif num_axes >= 3:
                    self.look_x = self._apply_deadzone(joy.get_axis(2))

                # Buttons: Shoot with Button 0 (A/Cross), Button 5 (RB/R1), or Button 7 (RT/R2)
                num_buttons = joy.get_num_buttons()
                pad_shoot = False
                if num_buttons > 0 and joy.get_button(0):
                    pad_shoot = True
                if num_buttons > 5 and joy.get_button(5):
                    pad_shoot = True
                if num_buttons > 7 and joy.get_button(7):
                    pad_shoot = True

                if pad_shoot and not self.pad_shoot_prev:
                    self.shoot_pressed = True
                self.pad_shoot_prev = pad_shoot

                # Buttons: Map with Button 1 (B/Circle), Button 8 (Select), or Button 9 (Start/L3)
                pad_map = False
                if num_buttons > 1 and joy.get_button(1):
                    pad_map = True
                if num_buttons > 8 and joy.get_button(8):
                    pad_map = True
                if num_buttons > 9 and joy.get_button(9):
                    pad_map = True

                if pad_map and not self.pad_map_prev:
                    self.map_pressed = True
                self.pad_map_prev = pad_map

            except Exception:
                pass

        # Check for double-flick UP gesture on right joystick to toggle mini-map
        self.update_double_flick()

    def update_double_flick(self):
        """
        Detects double-flick UP on the Right Joystick to toggle the 2D Mini-Map.
        Requires:
          1. Right Stick pushed UP (abs(look_y) > 0.45).
          2. Released back to neutral (abs(look_y) < 0.22).
          3. Pushed UP a second time within 800ms.
        """
        now = pg.time.get_ticks()

        # Right stick vertical push (UP)
        is_up = (abs(self.look_y) > 0.30)
        is_neutral = (abs(self.look_y) < 0.18)

        if self.flick_state == 0:  # IDLE
            if is_up:
                self.flick_first_time = now
                self.flick_state = 1
                print(f"[JOYSTICK] Right Stick Flick UP (1/2) [val={self.look_y:+.2f}]... Flick UP once more to open 2D Map!")

        elif self.flick_state == 1:  # WAITING_FOR_RELEASE
            if is_neutral:
                self.flick_state = 2
            elif now - self.flick_first_time > 800:
                self.flick_state = 0  # Timed out

        elif self.flick_state == 2:  # WAITING_FOR_SECOND_FLICK
            if is_up:
                self.map_pressed = True
                self.flick_state = 3
                print(f"[JOYSTICK] >>> DOUBLE FLICK UP [val={self.look_y:+.2f}] -> TOGGLED 2D MINI-MAP! <<<")
            elif now - self.flick_first_time > 950:
                self.flick_state = 0  # Timed out

        elif self.flick_state == 3:  # COOLDOWN (wait until stick returns to center)
            if is_neutral:
                self.flick_state = 0

    def get_movement(self):
        """Returns (move_x, move_y) where positive Y is forward, positive X is right."""
        return self.move_x, self.move_y

    def get_look(self):
        """Returns look_x where positive is turning right, negative is turning left."""
        return self.look_x

    def check_shoot_trigger(self):
        """Returns True once when shoot button is pressed down."""
        if self.shoot_pressed:
            self.shoot_pressed = False
            return True
        return False

    def check_map_trigger(self):
        """Returns True once when map button is pressed down."""
        if self.map_pressed:
            self.map_pressed = False
            return True
        return False

    def check_escape_trigger(self):
        """Returns True once when escape (Left Switch) is pressed down."""
        if self.escape_pressed:
            self.escape_pressed = False
            return True
        return False
