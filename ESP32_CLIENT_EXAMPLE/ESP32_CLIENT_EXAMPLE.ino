/**
 * ESP32-CAM WebSocket Client Code
 * Gửi ảnh từ ESP32-CAM đến Flask server qua WebSocket
 * 
 * Thư viện cần cài:
 * - WiFi (có sẵn)
 * - WebSocketsClient
 * - ArduinoJson
 * 
 * Cài thư viện: Tools -> Manage Libraries... -> Tìm "WebSocketsClient" by Markus Sattler
 */

#include <WiFi.h>
#include <WebSocketsClient.h>
#include "esp_camera.h"
#include <ArduinoJson.h>

// ================== CONFIGURATION ==================

// WiFi configuration
const char* ssid = "YOUR_SSID";           // Tên WiFi
const char* password = "YOUR_PASSWORD";   // Mật khẩu WiFi
const char* serverIP = "192.168.1.100";   // IP của máy tính chạy Flask
const int serverPort = 5000;              // Port của Flask

// Camera pins (OV2640 / OV7725 cho ESP32-CAM)
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

// ===================================================

WebSocketsClient webSocket;
camera_fb_t* fb = NULL;
int imageCount = 0;

void setup() {
    Serial.begin(115200);
    delay(10);
    
    Serial.println("\n\nESP32-CAM Trash Classification Client");
    Serial.println("=====================================");
    
    // Initialize camera
    if (!initCamera()) {
        Serial.println("❌ Camera init failed!");
        return;
    }
    Serial.println("✅ Camera initialized");
    
    // Connect WiFi
    connectWiFi();
    
    // WebSocket setup
    webSocket.begin(serverIP, serverPort, "/socket.io/?transport=websocket");
    webSocket.onEvent(webSocketEvent);
    webSocket.setReconnectInterval(5000);
    
    Serial.println("✅ Setup complete");
}

void loop() {
    webSocket.loop();
    
    // Capture and send image every 2 seconds
    if (millis() % 2000 == 0) {
        captureAndSend();
    }
}

/**
 * Initialize camera
 */
bool initCamera() {
    camera_config_t config;
    config.ledc_channel = LEDC_CHANNEL_0;
    config.ledc_timer = LEDC_TIMER_0;
    config.pin_d7 = Y9_GPIO_NUM;
    config.pin_d6 = Y8_GPIO_NUM;
    config.pin_d5 = Y7_GPIO_NUM;
    config.pin_d4 = Y6_GPIO_NUM;
    config.pin_d3 = Y5_GPIO_NUM;
    config.pin_d2 = Y4_GPIO_NUM;
    config.pin_d1 = Y3_GPIO_NUM;
    config.pin_d0 = Y2_GPIO_NUM;
    config.pin_vsync = VSYNC_GPIO_NUM;
    config.pin_href = HREF_GPIO_NUM;
    config.pin_pclk = PCLK_GPIO_NUM;
    config.pin_pwdn = PWDN_GPIO_NUM;
    config.pin_reset = RESET_GPIO_NUM;
    config.pin_xclk = XCLK_GPIO_NUM;
    config.pin_siod = SIOD_GPIO_NUM;
    config.pin_sioc = SIOC_GPIO_NUM;
    
    config.xclk_freq_hz = 20000000;
    config.pixel_format = PIXFORMAT_JPEG;
    config.frame_size = FRAMESIZE_QQVGA;  // 160x120 - nhỏ nhưng đủ tốc độ
    config.jpeg_quality = 12;              // 0-63, cao = chất lượng cao
    config.fb_count = 1;
    
    esp_err_t err = esp_camera_init(&config);
    if (err != ESP_OK) {
        return false;
    }
    return true;
}

/**
 * Connect to WiFi
 */
void connectWiFi() {
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
        Serial.println();
        Serial.print("✅ WiFi connected. IP: ");
        Serial.println(WiFi.localIP());
    } else {
        Serial.println();
        Serial.println("❌ Failed to connect WiFi");
    }
}

/**
 * Capture image and send to server
 */
void captureAndSend() {
    // Capture frame
    fb = esp_camera_fb_get();
    if (!fb) {
        Serial.println("❌ Camera capture failed");
        return;
    }
    
    if (webSocket.isConnected()) {
        // Send image via WebSocket
        // Note: WebSocket binary frame size limit, có thể cần compress
        
        // Cách 1: Gửi dưới dạng base64 (chậm hơn nhưng compatible)
        String imageData = base64_encode(fb->buf, fb->len);
        
        // Emit 'image' event với dữ liệu ảnh
        webSocket.sendTXT(String("{\"event\":\"image\",\"data\":\"") + imageData + "\"}");
        
        imageCount++;
        if (imageCount % 5 == 0) {
            Serial.print("📤 Images sent: ");
            Serial.println(imageCount);
        }
    }
    
    esp_camera_fb_return(fb);
}

/**
 * WebSocket event handler
 */
void webSocketEvent(WStype_t type, uint8_t * payload, size_t length) {
    switch(type) {
        case WStype_DISCONNECTED:
            Serial.println("📡 WebSocket disconnected");
            break;
            
        case WStype_CONNECTED:
            Serial.println("📡 WebSocket connected");
            Serial.print("   Server: ");
            Serial.print(serverIP);
            Serial.print(":");
            Serial.println(serverPort);
            break;
            
        case WStype_TEXT:
            handleMessage((char*)payload, length);
            break;
            
        case WStype_BIN:
            Serial.println("📡 Binary data received");
            break;
            
        case WStype_ERROR:
            Serial.println("❌ WebSocket error");
            break;
    }
}

/**
 * Handle message from server
 */
void handleMessage(char* payload, size_t length) {
    // Parse JSON
    StaticJsonDocument<200> doc;
    DeserializationError error = deserializeJson(doc, payload, length);
    
    if (error) {
        Serial.println("❌ JSON parse error");
        return;
    }
    
    // Extract result
    if (doc.containsKey("label")) {
        const char* label = doc["label"];
        float confidence = doc["confidence"];
        
        Serial.print("✅ Classification Result: ");
        Serial.print(label);
        Serial.print(" (");
        Serial.print(confidence);
        Serial.println(")");
        
        // TODO: Xử lý kết quả (VD: Điều khiển motor, servo, v.v.)
        // processResult(label, confidence);
    }
}

/**
 * Base64 encoding function
 * (Cần cài thư viện hoặc implement)
 */
String base64_encode(uint8_t* buffer, size_t length) {
    // Sử dụng thư viện "base64" hoặc ArduinoJson built-in encoding
    // Đây là placeholder
    return String("To implement base64 encoding");
}

/**
 * Optimize để tốc độ:
 * 1. FRAMESIZE_QQVGA (160x120) - nhỏ nhưng đủ tốc độ
 * 2. jpeg_quality = 12 - nén cao
 * 3. Gửi mỗi 2 giây - không quá nhiều
 * 4. Base64 encoding - có thể thay bằng binary nếu cần
 */
