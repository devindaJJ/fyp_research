// ============================================================
//  SMART PARKING SYSTEM — ESP32 Sensor Code
//  Components: ESP32 + HC-SR04 Ultrasonic Sensor
//  Connection: Phone Hotspot → HTTP POST to Flask backend
// ============================================================
//
//  WIRING GUIDE (copy this before you start):
//  HC-SR04 VCC  → ESP32 5V (or VIN)
//  HC-SR04 GND  → ESP32 GND
//  HC-SR04 TRIG → ESP32 GPIO 5
//  HC-SR04 ECHO → ESP32 GPIO 18
//
// ============================================================

#include <WiFi.h>
#include <HTTPClient.h>

// ------------------------------------------------------------
// STEP 1 — CHANGE THESE TO YOUR PHONE HOTSPOT DETAILS
// ------------------------------------------------------------
const char* WIFI_SSID     = "";       // your phone hotspot name
const char* WIFI_PASSWORD = "";   // your phone hotspot password

// ------------------------------------------------------------
// STEP 2 — CHANGE THIS TO YOUR BACKEND SERVER ADDRESS
// If your Flask backend is running on a laptop connected to
// the same hotspot, find that laptop's IP from cmd > ipconfig
// Example: "http://192.168.43.101:5000/api/parking/update"
// ------------------------------------------------------------
const char* BACKEND_URL = "http://192.168.8.189:8000/api/parking/update";

// ------------------------------------------------------------
// STEP 3 — SET YOUR SLOT DETAILS
// Hardcode the GPS coordinates of your parking slot here.
// You can get the exact lat/lng by dropping a pin in Google Maps.
// ------------------------------------------------------------
const char* SLOT_ID       = "SLOT_01";
const char* ZONE          = "Driveway";
const float SLOT_LAT      = 7.208430;    // replace with your actual latitude
const float SLOT_LNG      = 79.864670;   // replace with your actual longitude

// ------------------------------------------------------------
// SENSOR PIN CONFIGURATION
// ------------------------------------------------------------
const int TRIG_PIN = 5;
const int ECHO_PIN = 18;

// ------------------------------------------------------------
// DETECTION SETTINGS — tweak these if needed
// ------------------------------------------------------------
const float OCCUPIED_THRESHOLD_CM  = 50.0;  // if distance < 50cm = something is there
const int   VEHICLE_CONFIRM_SECS   = 15;    // must stay detected for 15 sec = real vehicle
const int   READING_INTERVAL_MS    = 500;   // read sensor every 500 milliseconds
const int   POST_INTERVAL_MS       = 5000;  // send data to server every 5 seconds

// ------------------------------------------------------------
// INTERNAL STATE — do not change these
// ------------------------------------------------------------
String  currentStatus       = "AVAILABLE";
String  lastSentStatus      = "";
unsigned long detectedSince = 0;
unsigned long lastPostTime  = 0;
bool    objectDetected      = false;

// ============================================================
//  SETUP — runs once when ESP32 powers on
// ============================================================
void setup() {
  Serial.begin(115200);
  delay(500);

  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);

  Serial.println("=================================");
  Serial.println("  Smart Parking System Starting ");
  Serial.println("=================================");

  connectToWiFi();
}

// ============================================================
//  MAIN LOOP — runs continuously
// ============================================================
void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi lost. Reconnecting...");
    connectToWiFi();
  }

  float distance = readDistance();

  Serial.print("Distance: ");
  Serial.print(distance);
  Serial.println(" cm");

  // --------------------------------------------------------
  // VEHICLE DETECTION LOGIC WITH TIME FILTER
  // This makes sure we only count a REAL parked vehicle,
  // not someone just walking past the sensor.
  // --------------------------------------------------------
  if (distance < OCCUPIED_THRESHOLD_CM && distance > 2.0) {
    if (!objectDetected) {
      objectDetected = true;
      detectedSince  = millis();
      Serial.println("Object detected — starting timer...");
    } else {
      unsigned long secondsDetected = (millis() - detectedSince) / 1000;

      if (secondsDetected >= VEHICLE_CONFIRM_SECS) {
        currentStatus = "OCCUPIED";
        Serial.print("VEHICLE CONFIRMED — occupied for ");
        Serial.print(secondsDetected);
        Serial.println(" seconds");
      } else {
        Serial.print("Waiting to confirm... ");
        Serial.print(secondsDetected);
        Serial.print(" / ");
        Serial.print(VEHICLE_CONFIRM_SECS);
        Serial.println(" sec");
      }
    }
  } else {
    if (objectDetected) {
      Serial.println("Object gone — slot now AVAILABLE");
    }
    objectDetected = false;
    detectedSince  = 0;
    currentStatus  = "AVAILABLE";
  }

  // --------------------------------------------------------
  // SEND DATA TO BACKEND EVERY 5 SECONDS
  // --------------------------------------------------------
  unsigned long now = millis();
  if (now - lastPostTime >= POST_INTERVAL_MS) {
    lastPostTime = now;
    sendToBackend(currentStatus, distance);
  }

  delay(READING_INTERVAL_MS);
}

// ============================================================
//  FUNCTION: Read distance from HC-SR04 sensor (returns cm)
// ============================================================
float readDistance() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  long duration = pulseIn(ECHO_PIN, HIGH, 30000); // 30ms timeout

  if (duration == 0) {
    return 999.0; // nothing in range
  }

  // d = (t * v) / 2  where v = 0.0343 cm/microsecond
  float distance = (duration * 0.0343) / 2.0;
  return distance;
}

// ============================================================
//  FUNCTION: Connect to WiFi / phone hotspot
// ============================================================
void connectToWiFi() {
  Serial.print("Connecting to hotspot: ");
  Serial.println(WIFI_SSID);

  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nConnected!");
    Serial.print("ESP32 IP: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\nFailed to connect. Will retry in loop.");
  }
}

// ============================================================
//  FUNCTION: Send parking status to Flask backend via HTTP POST
// ============================================================
void sendToBackend(String status, float distance) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("No WiFi — skipping POST");
    return;
  }

  HTTPClient http;
  http.begin(BACKEND_URL);
  http.addHeader("Content-Type", "application/json");

  // JSON payload includes slot info, status, distance, and GPS coords
  String payload = "{";
  payload += "\"slot_id\": \""   + String(SLOT_ID)       + "\", ";
  payload += "\"zone\": \""      + String(ZONE)           + "\", ";
  payload += "\"status\": \""    + status                 + "\", ";
  payload += "\"distance_cm\": " + String(distance, 1)    + ", ";
  payload += "\"latitude\": "    + String(SLOT_LAT, 6)    + ", ";
  payload += "\"longitude\": "   + String(SLOT_LNG, 6);
  payload += "}";

  Serial.println("Sending → " + payload);

  int responseCode = http.POST(payload);

  if (responseCode > 0) {
    Serial.print("Server response: ");
    Serial.println(responseCode);
    Serial.println(http.getString());
  } else {
    Serial.print("POST failed. Error code: ");
    Serial.println(responseCode);
  }

  http.end();
}
