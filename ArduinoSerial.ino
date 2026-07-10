#include <Servo.h>

// ─────────────────────────────────────────
//  SERVO OBJECTS
// ─────────────────────────────────────────
Servo servoThumb;
Servo servoIndex;
Servo servoMiddle;
Servo servoRing;
Servo servoPinky;

// ─────────────────────────────────────────
//  SERVO PINS (avoid 12, 13 on Nano)
// ─────────────────────────────────────────
#define PIN_THUMB   3
#define PIN_INDEX   5
#define PIN_MIDDLE  6
#define PIN_RING    9
#define PIN_PINKY   10

// ─────────────────────────────────────────
//  SERVO ANGLES
//  Adjust these if your hand is reversed
// ─────────────────────────────────────────
#define ANGLE_OPEN   180
#define ANGLE_CLOSED   0

// ─────────────────────────────────────────
//  SERIAL PROTOCOL
//  Python sends: $PRMIT\n  (6 chars total)
//  Each digit is 0 (closed) or 1 (open)
//  P = Pinky, R = Ring, M = Middle,
//  I = Index, T = Thumb
// ─────────────────────────────────────────
#define PACKET_LENGTH  6   // $ + 5 digits
#define START_MARKER   '$'

// ─────────────────────────────────────────
//  STATE VARIABLES
// ─────────────────────────────────────────
String  receivedString     = "";
int     stringCounter      = 0;
bool    receivingData      = false;
unsigned long lastByteTime = 0;

// Finger values (0 = closed, 1 = open)
int valPinky  = 0;
int valRing   = 0;
int valMiddle = 0;
int valIndex  = 0;
int valThumb  = 0;


// ─────────────────────────────────────────
//  SETUP
// ─────────────────────────────────────────
void setup() {
  Serial.begin(9600);

  servoThumb.attach(PIN_THUMB);
  servoIndex.attach(PIN_INDEX);
  servoMiddle.attach(PIN_MIDDLE);
  servoRing.attach(PIN_RING);
  servoPinky.attach(PIN_PINKY);

  // Start with hand fully closed
  allClosed();
  delay(500);

  Serial.println("Bionic Hand Ready — waiting for data...");
}


// ─────────────────────────────────────────
//  MAIN LOOP
// ─────────────────────────────────────────
void loop() {
  receiveData();
  updateServos();
}


// ─────────────────────────────────────────
//  RECEIVE & PARSE SERIAL DATA
// ─────────────────────────────────────────
void receiveData() {

  // Reset if no byte received for 300ms (corrupt/incomplete packet guard)
  if (millis() - lastByteTime > 300 && receivingData) {
    receivedString = "";
    stringCounter  = 0;
    receivingData  = false;
  }

  while (Serial.available()) {
    char c = Serial.read();
    lastByteTime = millis();

    // New packet starts — reset everything
    if (c == START_MARKER) {
      receivedString = "";
      stringCounter  = 0;
      receivingData  = true;
    }

    // Collect characters if inside a packet
    if (receivingData) {
      if (stringCounter < PACKET_LENGTH) {
        receivedString += c;
        stringCounter++;
      }

      // Full packet received — parse it
      if (stringCounter >= PACKET_LENGTH) {
        receivingData = false;
        stringCounter = 0;

        // Parse: $PRMIT
        // substring(1,2) = char after '$'
        valPinky  = receivedString.substring(1, 2).toInt();
        valRing   = receivedString.substring(2, 3).toInt();
        valMiddle = receivedString.substring(3, 4).toInt();
        valIndex  = receivedString.substring(4, 5).toInt();
        valThumb  = receivedString.substring(5, 6).toInt();

        // Debug feedback to Serial Monitor
        Serial.print("P:"); Serial.print(valPinky);
        Serial.print(" R:"); Serial.print(valRing);
        Serial.print(" M:"); Serial.print(valMiddle);
        Serial.print(" I:"); Serial.print(valIndex);
        Serial.print(" T:"); Serial.println(valThumb);

        receivedString = "";
      }
    }
  }
}


// ─────────────────────────────────────────
//  MOVE SERVOS BASED ON PARSED VALUES
// ─────────────────────────────────────────
void updateServos() {
  servoThumb.write (valThumb  == 1 ? ANGLE_OPEN : ANGLE_CLOSED);
  servoIndex.write (valIndex  == 1 ? ANGLE_OPEN : ANGLE_CLOSED);
  servoMiddle.write(valMiddle == 1 ? ANGLE_OPEN : ANGLE_CLOSED);
  servoRing.write  (valRing   == 1 ? ANGLE_OPEN : ANGLE_CLOSED);
  servoPinky.write (valPinky  == 1 ? ANGLE_OPEN : ANGLE_CLOSED);
}


// ─────────────────────────────────────────
//  UTILITY FUNCTIONS
// ─────────────────────────────────────────
void allOpen() {
  servoThumb.write(ANGLE_OPEN);
  servoIndex.write(ANGLE_OPEN);
  servoMiddle.write(ANGLE_OPEN);
  servoRing.write(ANGLE_OPEN);
  servoPinky.write(ANGLE_OPEN);
}

void allClosed() {
  servoThumb.write(ANGLE_CLOSED);
  servoIndex.write(ANGLE_CLOSED);
  servoMiddle.write(ANGLE_CLOSED);
  servoRing.write(ANGLE_CLOSED);
  servoPinky.write(ANGLE_CLOSED);
}
