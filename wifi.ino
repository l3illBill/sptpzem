#include <PZEM004Tv30.h>
#ifdef ESP8266
  #include <ESP8266WiFi.h>
#else // ESP32
  #include <WiFi.h>
#endif
#include <ModbusIP_ESP8266.h>
#include <WiFiClientSecure.h>
#include <UniversalTelegramBot.h>

// Wi-Fi credentials
const char* ssid = "SPT";
const char* password = "Mt027489650";


// ModbusIP object
ModbusIP mb;

// Static IP settings
IPAddress local_IP(192, 168, 4, 240);
IPAddress gateway(192, 168, 4, 1);
IPAddress subnet(255, 255, 252, 0);
IPAddress primaryDNS(8, 8, 8, 8);
IPAddress secondaryDNS(8, 8, 4, 4);

// PZEM module on Serial2 (pins 16, 17)
PZEM004Tv30 pzem(Serial2, 16, 17);

// Telegram client
WiFiClientSecure client;

void setup() {
    Serial.begin(115200);
    Serial2.begin(9600, SERIAL_8N1, 16, 17); // RS485 Communication

    // Connect to Wi-Fi
    WiFi.config(local_IP, gateway, subnet, primaryDNS, secondaryDNS);
    WiFi.begin(ssid, password);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println("\nWiFi connected");
    Serial.print("Assigned IP: ");
    Serial.println(WiFi.localIP());

    // Send IP Address to Telegram

    // Start Modbus server
    mb.server();

    // Initialize Modbus registers
    for (int i = 0; i <= 32; i++) {
        mb.addHreg(i, 0);
    }

    // Registers for reset functionality
    mb.addHreg(0x20, 0);
    mb.addHreg(0x21, 0);
    
}

void loop() {
    mb.task();
    delay(1000);

    // Read values from PZEM
    float voltage = pzem.voltage();
    float current = pzem.current();
    float power = pzem.power();
    float energy = pzem.energy();
    float frequency = pzem.frequency();
    float pf = pzem.pf();

    // Send values to Modbus
    sendFloatToModbus(voltage, 0);
    sendFloatToModbus(current, 2);
    sendFloatToModbus(power, 4);
    sendFloatToModbus(energy, 6);
    sendFloatToModbus(frequency, 8);
    sendFloatToModbus(pf, 10);

    // Check reset command
    if (mb.Hreg(0x20) == 1) {
        pzem.resetEnergy();
        mb.Hreg(0x20, 0); // Clear command after execution
    }

    // Print values to Serial Monitor
    Serial.print("Voltage: "); Serial.println(voltage);
    Serial.print("Current: "); Serial.println(current);
    Serial.print("Power: "); Serial.println(power);
    Serial.print("Energy: "); Serial.println(energy, 3);
    Serial.print("Frequency: "); Serial.println(frequency);
    Serial.print("Power Factor: "); Serial.println(pf);
    Serial.print("Reset Status: "); Serial.println(mb.Hreg(0x21));
    Serial.println("Sending data via Modbus...");
}

// Function to send reset command

// Function to convert float to Modbus registers
void sendFloatToModbus(float value, int startRegister) {
    uint32_t rawValue = *((uint32_t*)&value);
    uint16_t high = (rawValue >> 16) & 0xFFFF;
    uint16_t low = rawValue & 0xFFFF;

    mb.Hreg(startRegister, low);
    mb.Hreg(startRegister + 1, high);

    Serial.print("Low part (0x"); Serial.print(startRegister); Serial.print("): "); Serial.println(low);
    Serial.print("High part (0x"); Serial.print(startRegister + 1); Serial.print("): "); Serial.println(high);
}
