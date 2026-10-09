/*
  Arduino Joystick Pin Finder / Scanner
  Upload this sketch to test which pins your joysticks & buttons are connected to!
*/

void setup() {
  Serial.begin(115200);
  // Set all digital pins 2-9 with internal pullups for button testing
  for (int p = 2; p <= 9; p++) {
    pinMode(p, INPUT_PULLUP);
  }
  Serial.println("--- JOYSTICK PIN SCANNER READY ---");
  Serial.println("Move your sticks and press buttons to see which values change!");
}

void loop() {
  // Read all 6 analog pins
  int a0 = analogRead(A0);
  int a1 = analogRead(A1);
  int a2 = analogRead(A2);
  int a3 = analogRead(A3);
  int a4 = analogRead(A4);
  int a5 = analogRead(A5);

  // Read button pins (0 when pressed, 1 when released)
  int d2 = digitalRead(2);
  int d3 = digitalRead(3);
  int d4 = digitalRead(4);
  int d5 = digitalRead(5);
  int d6 = digitalRead(6);
  int d7 = digitalRead(7);
  int d8 = digitalRead(8);

  // Print readable line
  Serial.print("ANALOG -> A0:"); Serial.print(a0);
  Serial.print(" | A1:"); Serial.print(a1);
  Serial.print(" | A2:"); Serial.print(a2);
  Serial.print(" | A3:"); Serial.print(a3);
  Serial.print(" | A4:"); Serial.print(a4);
  Serial.print(" | A5:"); Serial.print(a5);

  Serial.print("  ||  BUTTONS -> D2:"); Serial.print(d2);
  Serial.print(" D3:"); Serial.print(d3);
  Serial.print(" D4:"); Serial.print(d4);
  Serial.print(" D5:"); Serial.print(d5);
  Serial.print(" D8:"); Serial.println(d8);

  delay(150);
}
