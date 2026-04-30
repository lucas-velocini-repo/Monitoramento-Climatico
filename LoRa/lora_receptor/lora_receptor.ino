#include <Arduino.h>
#include <SoftwareSerial.h>
#include "LoRa_E220.h"
#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <ArduinoJson.h>

// ========== DEFINIÇÃO DOS PINOS ==========
#define PIN_M0      12
#define PIN_M1      13
#define PIN_AUX     14
#define RX_PIN      4
#define TX_PIN      5

// ========== CONFIGURAÇÃO DE WIFI E SERVIDOR ============
const char* ssid = "WiFi_Notebook";
const char* password = "senha123";
const char* serverName = "http://192.168.137.1:5000/dados";
int postInterval = 0;
String dadosPost = "{\"Start\": \"Mensagem inicial\"}";

// ========== CONFIGURAÇÕES DESEJADAS ==========
const uint8_t MY_ADDR_HIGH = 0x00;
const uint8_t MY_ADDR_LOW  = 0x02;
const uint8_t MY_CHANNEL   = 23;
const long    MY_BAUD      = 9600;

// ========== OBJETOS GLOBAIS ==========
SoftwareSerial loraSerial(RX_PIN, TX_PIN);
LoRa_E220 lora(&loraSerial, PIN_AUX, PIN_M0, PIN_M1);

// ========== DECLARAÇÃO DAS FUNÇÕES ==========
void initPinsAndModule(int m0, int m1, int aux, long baud);
void readLoRaConfig(int m0, int m1, int aux);
void configureCommunicationParams(int m0, int m1, int aux, 
                                 uint8_t addrHigh, uint8_t addrLow, uint8_t channel,
                                 uint8_t airDataRate = AIR_DATA_RATE_010_24,
                                 uint8_t uartBaud = UART_BPS_9600,
                                 uint8_t txPower = POWER_22,
                                 bool fixedTx = true,
                                 bool rssiEnabled = true);
void configureAsReceiver(int m0, int m1, int aux);
void processReceivedMessage(const String& raw);

// ========== SETUP ==========
void setup() {
    Serial.begin(9600);
    while (!Serial);
    delay(2000);

    Serial.println("\n===================================");
    Serial.println(" Receptor LoRa E220 - NodeMCU");
    Serial.println("===================================");

    initPinsAndModule(PIN_M0, PIN_M1, PIN_AUX, MY_BAUD);
    readLoRaConfig(PIN_M0, PIN_M1, PIN_AUX);
    
    configureCommunicationParams(PIN_M0, PIN_M1, PIN_AUX,
                                 MY_ADDR_HIGH, MY_ADDR_LOW, MY_CHANNEL);
    
    configureAsReceiver(PIN_M0, PIN_M1, PIN_AUX);

    WiFi.begin(ssid, password);
    Serial.println("\nConfigurando WiFi...");
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
        }
    Serial.println("\nConectado ao Wi-Fi!");

    Serial.println("\nReceptor pronto. Aguardando mensagens...\n");
}

// ========== LOOP ==========
void loop() {
    if (lora.available() > 0) {
        ResponseContainer rc = lora.receiveMessage();
        if (rc.status.code == 1) {
            String rawData = String(rc.data);
            dadosPost = rawData;
            sendPost(dadosPost);
            //processReceivedMessage(rawData);
        } else {
            Serial.print("Erro: ");
            Serial.println(rc.status.getResponseDescription());
        }
    }
    delay(50);
}

void sendPost(const String& dados){

    if(WiFi.status()== WL_CONNECTED){
        WiFiClient client;
        HTTPClient http;
        
        // Inicia conexão HTTP
        http.begin(client, serverName);
        
        // Define o tipo de conteúdo para JSON
        http.addHeader("Content-Type", "application/json");

        Serial.println("Dados enviados post: " + dados);
        
        // Envia o POST
        int httpResponseCode = http.POST("{\"Teste\": \"Teste de mensagem post.\"}");
        
        if (httpResponseCode > 0) {
        String response = http.getString();
        Serial.println(httpResponseCode);
        Serial.println(response);
        } else {
        Serial.print("Erro na requisição: ");
        Serial.println(httpResponseCode);
        }
        
        // Finaliza
        http.end();
        }
        else {
            Serial.println("WiFi Desconectado");
        }
}

// ========== PROCESSAMENTO DA MENSAGEM ==========
void processReceivedMessage(const String& raw) {
    // Limpeza: remove caracteres não imprimíveis (exceto espaço, vírgula, ponto, números, letras)
    String clean;
    for (char c : raw) {
        if (isPrintable(c) || c == '\n' || c == '\r') {
            clean += c;
        }
    }
    clean.trim();

    if (clean.length() == 0) {
        Serial.println("Mensagem vazia ou apenas caracteres inválidos.");
        return;
    }

    Serial.print("Recebido (bruto): ");
    Serial.println(raw);
    Serial.print("Limpo: ");
    Serial.println(clean);

    // Tentativa 1: Parse como JSON
    StaticJsonDocument<200> doc;
    DeserializationError error = deserializeJson(doc, clean);

    if (!error) {
        // É JSON válido
        const char* id = doc["id"] | "null";
        const char* tp = doc["tp"] | "null";
        JsonObject dt = doc["dt"];

        // Q pode ser número inteiro ou float
        float Q = dt["Q"] | -1.0f;
        int I = dt["I"] | -1;
        int N = dt["N"] | -1;

        // Imprime no formato CSV
        Serial.print(id);
        Serial.print(",");
        Serial.print(tp);
        Serial.print(",");
        Serial.print(Q, 2);   // Duas casas decimais para Q
        Serial.print(",");
        Serial.print(I);
        Serial.print(",");
        Serial.println(N);
        return;
    }

    // Tentativa 2: Parse como CSV simples (formato: id,tp,Q,I,N)
    // Exemplo: "p01,u,0,12.45,1"
    int comma1 = clean.indexOf(',');
    int comma2 = clean.indexOf(',', comma1 + 1);
    int comma3 = clean.indexOf(',', comma2 + 1);
    int comma4 = clean.indexOf(',', comma3 + 1);

    if (comma1 != -1 && comma2 != -1 && comma3 != -1 && comma4 != -1) {
        String id    = clean.substring(0, comma1);
        String tp    = clean.substring(comma1 + 1, comma2);
        String Q_str = clean.substring(comma2 + 1, comma3);
        String I_str = clean.substring(comma3 + 1, comma4);
        String N_str = clean.substring(comma4 + 1);

        float Q = Q_str.toFloat();
        int I = I_str.toInt();
        int N = N_str.toInt();

        Serial.print(id);
        Serial.print(",");
        Serial.print(tp);
        Serial.print(",");
        Serial.print(Q, 2);
        Serial.print(",");
        Serial.print(I);
        Serial.print(",");
        Serial.println(N);
        return;
    }

    // Se chegou aqui, não conseguiu parsear
    Serial.print("Formato desconhecido: ");
    Serial.println(clean);
}

// ========== IMPLEMENTAÇÃO DAS DEMAIS FUNÇÕES (INALTERADAS) ==========

void initPinsAndModule(int m0, int m1, int aux, long baud) {
    pinMode(m0, OUTPUT);
    pinMode(m1, OUTPUT);
    pinMode(aux, INPUT);
    digitalWrite(m0, LOW);
    digitalWrite(m1, LOW);

    loraSerial.begin(baud);
    delay(200);

    if (!lora.begin()) {
        Serial.println("ERRO: Falha ao inicializar o módulo LoRa!");
        while (1);
    }
    Serial.println("Módulo inicializado.");
}

void readLoRaConfig(int m0, int m1, int aux) {
    Serial.println("\n📡 Lendo configuração atual...");

    digitalWrite(m0, HIGH);
    digitalWrite(m1, HIGH);
    delay(300);

    ResponseStructContainer c = lora.getConfiguration();
    if (c.status.code != 1) {
        Serial.println("❌ Falha ao ler configuração!");
        return;
    }

    Configuration config = *(Configuration*)c.data;
    Serial.println("=== Configuração Atual ===");
    Serial.print("Endereço: 0x");
    Serial.print(config.ADDH, HEX);
    Serial.print(" ");
    Serial.println(config.ADDL, HEX);
    Serial.print("Canal: ");
    Serial.println(config.CHAN);
    Serial.print("Taxa de ar: ");
    Serial.println(config.SPED.airDataRate);
    Serial.print("Baudrate UART: ");
    Serial.println(config.SPED.uartBaudRate);
    Serial.print("Potência TX: ");
    Serial.println(config.OPTION.transmissionPower);
    Serial.print("Transmissão Fixa: ");
    Serial.println(config.TRANSMISSION_MODE.fixedTransmission ? "Sim" : "Não");
    Serial.print("RSSI Habilitado: ");
    Serial.println(config.TRANSMISSION_MODE.enableRSSI ? "Sim" : "Não");
    Serial.println("==========================");

    c.close();

    digitalWrite(m0, LOW);
    digitalWrite(m1, LOW);
    delay(300);
    while (digitalRead(aux) == LOW) delay(50);
}

void configureCommunicationParams(int m0, int m1, int aux, 
                                 uint8_t addrHigh, uint8_t addrLow, uint8_t channel,
                                 uint8_t airDataRate, uint8_t uartBaud, uint8_t txPower,
                                 bool fixedTx, bool rssiEnabled) {
    Serial.println("\n⚙️ Verificando necessidade de configuração...");

    digitalWrite(m0, HIGH);
    digitalWrite(m1, HIGH);
    delay(300);

    ResponseStructContainer c = lora.getConfiguration();
    if (c.status.code != 1) {
        Serial.println("❌ Não foi possível ler configuração atual.");
        return;
    }

    Configuration config = *(Configuration*)c.data;
    bool precisaConfig = false;

    if (config.ADDH != addrHigh) {
        config.ADDH = addrHigh;
        precisaConfig = true;
    }
    if (config.ADDL != addrLow) {
        config.ADDL = addrLow;
        precisaConfig = true;
    }
    if (config.CHAN != channel) {
        config.CHAN = channel;
        precisaConfig = true;
    }
    if (config.TRANSMISSION_MODE.fixedTransmission != (fixedTx ? FT_FIXED_TRANSMISSION : FT_TRANSPARENT_TRANSMISSION)) {
        config.TRANSMISSION_MODE.fixedTransmission = fixedTx ? FT_FIXED_TRANSMISSION : FT_TRANSPARENT_TRANSMISSION;
        precisaConfig = true;
    }
    if (config.TRANSMISSION_MODE.enableRSSI != (rssiEnabled ? RSSI_ENABLED : RSSI_DISABLED)) {
        config.TRANSMISSION_MODE.enableRSSI = rssiEnabled ? RSSI_ENABLED : RSSI_DISABLED;
        precisaConfig = true;
    }
    if (config.SPED.airDataRate != airDataRate) {
        config.SPED.airDataRate = airDataRate;
        precisaConfig = true;
    }
    if (config.SPED.uartBaudRate != uartBaud) {
        config.SPED.uartBaudRate = uartBaud;
        precisaConfig = true;
    }
    if (config.OPTION.transmissionPower != txPower) {
        config.OPTION.transmissionPower = txPower;
        precisaConfig = true;
    }

    if (precisaConfig) {
        Serial.println("⚙️ Aplicando nova configuração...");
        ResponseStatus rs = lora.setConfiguration(config, WRITE_CFG_PWR_DWN_SAVE);
        if (rs.code != 1) {
            Serial.println("❌ Falha na configuração!");
            c.close();
            return;
        }
        Serial.println("✅ Configuração aplicada e salva na EEPROM.");
        delay(800);
    } else {
        Serial.println("✅ Configuração já está correta.");
    }

    c.close();

    digitalWrite(m0, LOW);
    digitalWrite(m1, LOW);
    delay(300);
    while (digitalRead(aux) == LOW) delay(50);
}

void configureAsReceiver(int m0, int m1, int aux) {
    Serial.println("🔊 Configurando como receptor (modo normal)...");
    digitalWrite(m0, LOW);
    digitalWrite(m1, LOW);
    delay(100);
    while (digitalRead(aux) == LOW) delay(50);
    Serial.println("✅ Pronto para receber.");
}
