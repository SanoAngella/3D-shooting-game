/*
 * Dual Joystick Controller for 3D Shooting Game
 * 
 * CONTROLS:
 *  - Left Stick (A0, A1): Movement (Walk & Strafe)
 *  - Left Switch (Pin 2 or Pin 8): ESCAPE (Quit Game)
 *  - Right Stick (A2, and auto-detect A3/A4/A5): Aim / Camera Rotation & Up/Down
 *  - Right Stick DOUBLE FLICK UP: TOGGLE 2D MINI-MAP!
 *  - Right Switch (Pin 3, 4, or Pin 9): SHOOT SHOTGUN!
 */

#include <SoftwareSerial.h>

// Bluetooth SoftwareSerial on Pin 10 (RX) and Pin 9 (TX)
// Wiring: HC-05 TXD -> Arduino Pin 10, HC-05 RXD -> Arduino Pin 9
SoftwareSerial btSerial(10, 9);

// --- ANALOG PIN CONFIGURATION ---
const int PIN_MOVE_X = A0;  // Strafe Left/Right
const int PIN_MOVE_Y = A1;  // Walk Forward/Backward
const int PIN_LOOK_X = A2;  // Rotate Camera Left/Right

// Candidate pins for Right Stick Up/Down (auto-detects whichever pin moves between A3, A4, A5)
const int LOOK_Y_CANDIDATES[] = {A3, A4, A5};
const int NUM_LOOK_Y = sizeof(LOOK_Y_CANDIDATES) / sizeof(LOOK_Y_CANDIDATES[0]);
int center_look_y[NUM_LOOK_Y];

// --- DIGITAL SWITCH CANDIDATE PINS ---
const int LEFT_SW_PINS[]  = {2, 8};        // Left Switch -> ESCAPE
const int RIGHT_SW_PINS[] = {3, 4};        // Right Switch -> SHOOT (Pin 9 removed: reserved for Bluetooth TX)

const int NUM_LEFT_PINS  = sizeof(LEFT_SW_PINS)  / sizeof(LEFT_SW_PINS[0]);
const int NUM_RIGHT_PINS = sizeof(RIGHT_SW_PINS) / sizeof(RIGHT_SW_PINS[0]);

int idle_left[NUM_LEFT_PINS];
int idle_right[NUM_RIGHT_PINS];

int center_move_x = 512;
int center_move_y = 512;
int center_look_x = 512;
const int DEADZONE = 50;

float readAxis(int pin, int center, bool invert = false) {
  int raw = analogRead(pin);
  int diff = raw - center;
  
  if (abs(diff) < DEADZONE) {
    return 0.0f;
  }
  
  float span = (diff > 0) ? (1023.0f - center - DEADZONE) : (center - DEADZONE);
  if (span <= 10.0f) span = 450.0f;
  
  float val = (diff > 0) ? (float)(diff - DEADZONE) / span
                         : (float)(diff + DEADZONE) / span;
                         
  if (val > 1.0f) val = 1.0f;
  if (val < -1.0f) val = -1.0f;
  
  return invert ? -val : val;
}

void setup() {
  Serial.begin(115200);   // Keep USB Serial active (for wired testing/debugging)
  btSerial.begin(9600);    // HC-05 Bluetooth Serial (for wireless gaming)

  // Setup Left Switch candidate pins with pull-ups
  for (int i = 0; i < NUM_LEFT_PINS; i++) {
    pinMode(LEFT_SW_PINS[i], INPUT_PULLUP);
  }
  // Setup Right Switch candidate pins with pull-ups
  for (int i = 0; i < NUM_RIGHT_PINS; i++) {
    pinMode(RIGHT_SW_PINS[i], INPUT_PULLUP);
  }

  // Allow voltage to settle, then calibrate resting centers & idle button states
  delay(350);

  center_move_x = analogRead(PIN_MOVE_X);
  center_move_y = analogRead(PIN_MOVE_Y);
  center_look_x = analogRead(PIN_LOOK_X);

  for (int i = 0; i < NUM_LOOK_Y; i++) {
    center_look_y[i] = analogRead(LOOK_Y_CANDIDATES[i]);
  }

  for (int i = 0; i < NUM_LEFT_PINS; i++) {
    idle_left[i] = digitalRead(LEFT_SW_PINS[i]);
  }
  for (int i = 0; i < NUM_RIGHT_PINS; i++) {
    idle_right[i] = digitalRead(RIGHT_SW_PINS[i]);
  }
}

void loop() {
  // Read analog axes (-1.0 to 1.0)
  float moveX = readAxis(PIN_MOVE_X, center_move_x);
  float moveY = readAxis(PIN_MOVE_Y, center_move_y, true); // Inverted so pushing UP = walk forward
  float lookX = readAxis(PIN_LOOK_X, center_look_x);

  // Auto-detect which pin (A3, A4, or A5) is being moved for Right Stick Up/Down
  int maxDiff = 0;
  int activeIndex = 0;
  for (int i = 0; i < NUM_LOOK_Y; i++) {
    int diff = abs(analogRead(LOOK_Y_CANDIDATES[i]) - center_look_y[i]);
    if (diff > maxDiff) {
      maxDiff = diff;
      activeIndex = i;
    }
  }
  float lookY = readAxis(LOOK_Y_CANDIDATES[activeIndex], center_look_y[activeIndex], true);

  // Detect Left Switch (Escape)
  int btnEscape = 0;
  for (int i = 0; i < NUM_LEFT_PINS; i++) {
    if (digitalRead(LEFT_SW_PINS[i]) != idle_left[i]) {
      btnEscape = 1;
      break;
    }
  }

  // Detect Right Switch (Shoot)
  int btnShoot = 0;
  for (int i = 0; i < NUM_RIGHT_PINS; i++) {
    if (digitalRead(RIGHT_SW_PINS[i]) != idle_right[i]) {
      btnShoot = 1;
      break;
    }
  }

  // Format: moveX,moveY,btnEscape,lookX,lookY,btnShoot

  // 1. Send over USB Serial
  Serial.print(moveX, 2);
  Serial.print(",");
  Serial.print(moveY, 2);
  Serial.print(",");
  Serial.print(btnEscape);
  Serial.print(",");
  Serial.print(lookX, 2);
  Serial.print(",");
  Serial.print(lookY, 2);
  Serial.print(",");
  Serial.println(btnShoot);

  // 2. Send over Bluetooth Wireless Serial
  btSerial.print(moveX, 2);
  btSerial.print(",");
  btSerial.print(moveY, 2);
  btSerial.print(",");
  btSerial.print(btnEscape);
  btSerial.print(",");
  btSerial.print(lookX, 2);
  btSerial.print(",");
  btSerial.print(lookY, 2);
  btSerial.print(",");
  btSerial.println(btnShoot);

  delay(25); // ~40 updates per second (smooth and reliable for 9600 baud wireless)
}
