#include <WiFi.h>
#include <HTTPClient.h>
#include <time.h>

const char* ssid = "SLT-4G_5938F0";
const char* password = "A668CBFD";
const char* scriptURL = "https://script.google.com/macros/s/AKfycbwljWC1x9h_eLQYodU35iE4RULRjtLuExkrQO6VjBA3lw8OiTs-P--FhSWI1Z_yfz87/exec";

// Sensor Pins
const int trigPin = 13;    
const int echoPin = 12;   
const int hallPin = 27;   

// Parking Configuration
const float PARKING_THRESHOLD = 30.0;   
const int HALL_THRESHOLD = 2000;        
const long PARKING_TIMEOUT = 120000;    

// Upload Settings
const long UPLOAD_INTERVAL = 10000;    
const long SENSOR_READ_INTERVAL = 2000; 

// Location Tag (set your location)
const String LOCATION = "Colombo_Parking";

unsigned long lastUploadTime = 0;
unsigned long lastSensorReadTime = 0;
unsigned long parkingStartTime = 0;
bool isParkingOccupied = false;
bool lastParkingState = false;
float currentDistance = 0;
int currentHallValue = 0;
String vehicleDetected = "NO";
long parkingDuration = 0;

void setup() {
  Serial.begin(115200);
  Serial.println("\n===== PARKING DETECTION SYSTEM =====");
  
  pinMode(trigPin, OUTPUT);
  pinMode(echoPin, INPUT);
  pinMode(hallPin, INPUT);
  connectToWiFi();
  configTime(0, 0, "pool.ntp.org");
  
  Serial.println("System initialized!");
  Serial.println("================================");
}
void loop() {
  unsigned long currentTime = millis();
  
  if (currentTime - lastSensorReadTime >= SENSOR_READ_INTERVAL) {
    readSensors();
    checkParkingStatus();
    lastSensorReadTime = currentTime;
  }
  
  if (currentTime - lastUploadTime >= UPLOAD_INTERVAL) {
    uploadParkingData();
    lastUploadTime = currentTime;
  }
  
  delay(100);
}

// Connect to WiFi
void connectToWiFi() {
  Serial.print("Connecting to WiFi: ");
  Serial.println(ssid);
  
  WiFi.begin(ssid, password);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi Connected!");
    Serial.print("IP Address: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\nWiFi Connection Failed!");
  }
}

// Read ultrasonic sensor distance
float readUltrasonicDistance() {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);
  
  long duration = pulseIn(echoPin, HIGH, 30000); 
  
  if (duration == 0) {
    return -1; 
  }
  
  float distance = duration * 0.0343 / 2; 
  
  if (distance < 2 || distance > 400) {
    return -1; 
  }
  
  return distance;
}

int readHallSensor() {
  int sum = 0;
  for (int i = 0; i < 5; i++) {
    sum += analogRead(hallPin);
    delay(2);
  }
  return sum / 5;
}

void readSensors() {
  currentDistance = readUltrasonicDistance();
  currentHallValue = readHallSensor();
  
  Serial.println("===== Sensor Readings =====");
  Serial.print("Distance: ");
  if (currentDistance < 0) {
    Serial.println("INVALID");
  } else {
    Serial.print(currentDistance);
    Serial.println(" cm");
  }
  
  Serial.print("Hall Value: ");
  Serial.println(currentHallValue);
  Serial.println("==========================");
}

void checkParkingStatus() {
  bool ultrasonicOccupied = (currentDistance > 0 && currentDistance < PARKING_THRESHOLD);
  bool hallOccupied = (currentHallValue > HALL_THRESHOLD);
  
  isParkingOccupied = (ultrasonicOccupied && hallOccupied);
  vehicleDetected = isParkingOccupied ? "YES" : "NO";
  
  unsigned long currentTime = millis();
  
  if (isParkingOccupied && !lastParkingState) {
    parkingStartTime = currentTime;
    Serial.println("VEHICLE DETECTED - Parking started");
  } 
  else if (!isParkingOccupied && lastParkingState) {
    parkingDuration = (currentTime - parkingStartTime) / 1000;
    Serial.print("VEHICLE LEFT - Parking duration: ");
    Serial.print(parkingDuration);
    Serial.println(" seconds");
    
    if (parkingDuration > (PARKING_TIMEOUT / 1000)) {
      Serial.println(" ILLEGAL PARKING DETECTED!");
    }
  }
  else if (isParkingOccupied) {
    parkingDuration = (currentTime - parkingStartTime) / 1000;
  }
  
  lastParkingState = isParkingOccupied;
  
  Serial.print("Status: ");
  Serial.println(isParkingOccupied ? "OCCUPIED" : "VACANT");
  if (isParkingOccupied) {
    Serial.print("Duration: ");
    Serial.print(parkingDuration);
    Serial.println(" seconds");
  }
  Serial.println();
}

String getTimestamp() {
  struct tm timeinfo;
  if (!getLocalTime(&timeinfo)) {
    return String(millis());
  }
  
  char timeString[20];
  strftime(timeString, sizeof(timeString), "%H:%M:%S", &timeinfo);
  return String(timeString);
}

void uploadParkingData() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi not connected! Reconnecting...");
    connectToWiFi();
    return;
  }
  
  HTTPClient http;
  
  String url = String(scriptURL);
  url += "?action=parking";
  url += "&timestamp=" + getTimestamp();
  url += "&distance=" + String(currentDistance, 1);
  url += "&vehicle_detected=" + vehicleDetected;
  url += "&parking_duration=" + String(parkingDuration);
  url += "&location=" + LOCATION;
  
  Serial.println("===== Uploading Data =====");
  Serial.print("URL: ");
  Serial.println(url);
  
  http.begin(url);
  http.setTimeout(10000);
  http.setFollowRedirects(HTTPC_FORCE_FOLLOW_REDIRECTS);
  

  int httpCode = http.GET();
  
  if (httpCode > 0) {
    String response = http.getString();
    Serial.print("Response Code: ");
    Serial.println(httpCode);
    Serial.print("Response: ");
    Serial.println(response);
    
    if (response.indexOf("success") >= 0 || response.indexOf("logged") >= 0) {
      Serial.println("Data uploaded successfully!");
    } else {
      Serial.println("Upload completed but check response");
    }
  } else {
    Serial.print("Upload failed! Error: ");
    Serial.println(http.errorToString(httpCode).c_str());
    
    if (httpCode == HTTPC_ERROR_CONNECTION_REFUSED || 
        httpCode == HTTPC_ERROR_CONNECTION_LOST) {
      WiFi.disconnect();
      connectToWiFi();
    }
  }
  
  http.end();
  Serial.println("==========================");
  Serial.println();
}

void testSensors() {
  Serial.println("\n===== SENSOR TEST =====");
  
  for (int i = 0; i < 5; i++) {
    float dist = readUltrasonicDistance();
    int hall = readHallSensor();
    
    Serial.print("Test ");
    Serial.print(i + 1);
    Serial.print(": Distance = ");
    Serial.print(dist);
    Serial.print(" cm, Hall = ");
    Serial.println(hall);
    
    delay(1000);
  }
  
  Serial.println("===== TEST COMPLETE =====");
}

// Get WiFi signal strength
int getWiFiStrength() {
  if (WiFi.status() != WL_CONNECTED) return 0;
  return WiFi.RSSI();
}

// Print system status
void printSystemStatus() {
  Serial.println("\n===== SYSTEM STATUS =====");
  Serial.print("WiFi: ");
  Serial.println(WiFi.status() == WL_CONNECTED ? "Connected" : "Disconnected");
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("Signal: ");
    Serial.print(getWiFiStrength());
    Serial.println(" dBm");
    Serial.print("IP: ");
    Serial.println(WiFi.localIP());
  }
  
  Serial.print("Parking Status: ");
  Serial.println(isParkingOccupied ? "OCCUPIED" : "VACANT");
  Serial.print("Vehicle Detected: ");
  Serial.println(vehicleDetected);
  Serial.print("Current Distance: ");
  Serial.print(currentDistance);
  Serial.println(" cm");
  Serial.print("Hall Value: ");
  Serial.println(currentHallValue);
  Serial.println("==========================");
}