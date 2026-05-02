#include <TinyGPS++.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <LiquidCrystal_I2C.h>
LiquidCrystal_I2C lcd(0x27, 16, 2);
// WiFi
const char* ssid = "SLT-Fiber-KYhN6-2.4G";
const char* password = "19641125";
// Google Sheets
String scriptURL = "https://script.google.com/macros/s/AKfycbw6WUs1RVvBWryJvn9FrgzuOpy18tNlt5LiH7wlknBw5wCo6x4X6FSHzUzTGS3JkW8wFw/exec";
const int xPin = 34;
const int yPin = 35;
const int zPin = 36; 
const int trigPin = 13;    // GPIO13
const int echoPin = 12;    // GPIO12
const byte interruptPin = 14;     // GPIO14
volatile bool vibrationDetected = false;
void IRAM_ATTR handleVibration() {
  vibrationDetected = true; 
}
#define RXD2 16
#define TXD2 17
TinyGPSPlus gps;
float lat;
float lng;
float distance;
HardwareSerial gpsSerial(2);
const int crashThreshold = 3000;
int impactCount = 0;


void setup() {
 pinMode(trigPin, OUTPUT);
 pinMode(echoPin, INPUT);
 pinMode(interruptPin, INPUT_PULLUP);
 attachInterrupt(digitalPinToInterrupt(interruptPin), handleVibration, FALLING);
 lcd.begin(16, 2);
 lcd.setCursor(0, 0);
 lcd.print("car accident"); 
 lcd.setCursor(0, 1);
 lcd.print("monitor system");
Serial.begin(9600);
WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nConnected!");
pinMode(xPin, INPUT);
pinMode(yPin, INPUT);
pinMode(zPin, INPUT); 
gpsSerial.begin(9600, SERIAL_8N1, RXD2, TXD2);
Serial.println("GPS WL_CONNECTED...");

}

void loop() {
 Accelerometer(); 
 readUltrasonic();
  
  
  
  if (vibrationDetected) {
    
    Serial.println("Vibration Detected!");
     impactCount++;
   
    
    
    
  }
}

void displayInfo() {
  if (gps.location.isValid()) {
     lat = gps.location.lat();
     lng = gps.location.lng();
   
   
    Serial.print(lat,6);
    Serial.print(", ");
    Serial.println(lng,6);
    
    
  } else {
    Serial.println("GPS Error");
  }
 
}
void Accelerometer(){
  
 int xVal = analogRead(xPin);
 int yVal = analogRead(yPin);
 int zVal = analogRead(zPin); 
  if ((xVal > crashThreshold || yVal > crashThreshold || zVal > crashThreshold)||((vibrationDetected==true)&&(distance<100))) {
    Serial.println("!!! CRASH DETECTED !!!");
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print(" CRASH DETECTED ");
    delay(2000);
    Gps();
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print(String("Lat ") + lat);
    lcd.setCursor(0, 1); 
    lcd.print(String("Lng: ") + lng);
    
   
    sendToGoogle();
    
    delay(5000); // 
  } 
  
vibrationDetected = false;
  delay(500);
 }
 void sendToGoogle() {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    
  
    

    String url = scriptURL + "?Latitude=" + String(lat,6) + "&Longitud=" + String(lng,6)+ "&Vibration=" + String(vibrationDetected)+ "&Distance=" + String(distance);
    
    http.begin(url.c_str());
    http.setFollowRedirects(HTTPC_STRICT_FOLLOW_REDIRECTS);
    int httpCode = http.GET();
    
    if (httpCode > 0) {
      Serial.println("Data Sent Successfully! Status: " + String(httpCode));
    } else {
      Serial.println("Error sending data");
    }
    http.end();
  }
  
}



void Gps(){
  while (gpsSerial.available() > 0) {
    if (gps.encode(gpsSerial.read())) {
      displayInfo();
    }
  }
}
void readUltrasonic() {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);
  
  long duration = pulseIn(echoPin, HIGH);
  distance= duration * 0.0343 / 2;
  Serial.println(distance);
}