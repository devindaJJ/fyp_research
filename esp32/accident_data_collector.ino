#include <WiFi.h>
#include <HTTPClient.h>

// WiFi
const char* ssid = "";
const char* password = "";

// Google Sheets
const char* googleURL = "";

// Pins for ESP32
const int trigPin = 13;    // GPIO13
const int echoPin = 12;    // GPIO12
const int vibPin = 14;     // GPIO14

// Impact counter
int impactCount = 0;

void setup() {
  Serial.begin(115200);
  
  // Setup pins
  pinMode(trigPin, OUTPUT);
  pinMode(echoPin, INPUT);
  pinMode(vibPin, INPUT_PULLUP);
  
  // Connect to WiFi
  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nConnected!");
}

void loop() {
  // Read distance
  float distance = readUltrasonic();
  
  // Read vibration (LOW means vibrating)
  bool vibrating = (digitalRead(vibPin) == LOW);
  
  // Count impacts
  if (vibrating) {
    impactCount++;
    Serial.println("IMPACT DETECTED!");
  }
  
  // Print to Serial
  Serial.print("Distance: ");
  Serial.print(distance);
  Serial.print("cm | Vibration: ");
  Serial.println(vibrating ? "YES" : "NO");
  
  // Send to Google Sheets every 10 seconds
  static unsigned long lastSend = 0;
  if (millis() - lastSend > 10000) {
    sendToGoogle(distance, vibrating);
    lastSend = millis();
  }
  
  delay(100);
}

float readUltrasonic() {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);
  
  long duration = pulseIn(echoPin, HIGH);
  return duration * 0.0343 / 2;
}

void sendToGoogle(float distance, bool vibrating) {
  String url = String(googleURL);
  
  // FIXED: Convert everything to String() before concatenation
  url += "?timestamp=" + String(millis());
  url += "&device=ESP32_CAR";
  url += "&distance=" + String(distance, 2);
  
  // FIXED LINE: Use String() for the conditional
  url += "&impact=" + String(vibrating ? "YES" : "NO");
  
  url += "&impact_count=" + String(impactCount);
  url += "&rssi=" + String(WiFi.RSSI());
  
  Serial.println("Sending: " + url);
  
  HTTPClient http;
  http.begin(url);
  int code = http.GET();
  Serial.println("Response: " + String(code));
  http.end();
}