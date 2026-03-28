#include <Arduino.h>
#include "FS.h"
#include "SD.h"
#include "SPI.h"
#include <driver/i2s.h>
#include <WiFi.h>
#include <HTTPClient.h>

// ===== Wi-Fi e Servidor =====
const char* ssid = "WiFi Notebook";
const char* password = "senha123";
const char* serverUrl = "http://192.168.137.1:9000/sensores/alerta/beepsonoro";

// Variáveis de controle de tempo
unsigned long ultimoCheck = 0;
const long intervalo = 5000; // 5000ms = 5 segundos

// --- PINAGEM DO USUÁRIO ---
// SD Card (SPI)
#define SD_CS      10    // Confirme se na sua placa é 10 ou 7 (ESP32-C3 SuperMini costuma ser 7)
#define SPI_MOSI   3
#define SPI_MISO   2
#define SPI_SCK    4

// I2S (MAX98357)
#define I2S_BCLK   19
#define I2S_LRC    18
#define I2S_DOUT   21

// Configurações do Arquivo WAV
#define SAMPLE_RATE 44100 
#define I2S_NUM I2S_NUM_0

File audioFile;
bool tocandoAudio = false; // Flag para saber se deve tocar
uint8_t buffer[512];       // Buffer de áudio

// --- Funções Auxiliares ---

void conectarWiFi() {
  Serial.print("Conectando ao WiFi: ");
  Serial.println(ssid);
  
  WiFi.begin(ssid, password);
  
  int tentativas = 0;
  while (WiFi.status() != WL_CONNECTED && tentativas < 20) {
    delay(500);
    Serial.print(".");
    tentativas++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi Conectado!");
    Serial.print("IP: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\nFalha na conexão WiFi. Verifique as credenciais.");
  }
}

void verificarServidor() {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(serverUrl);
    
    Serial.println("Consultando servidor...");
    int httpResponseCode = http.GET();
    
    if (httpResponseCode > 0) {
      String payload = http.getString();
      payload.trim(); // Remove espaços em branco extras
      Serial.print("Resposta do servidor: ");
      Serial.println(payload);

      if (payload == "1") {
        // Prepara para tocar
        if (!tocandoAudio) {
          // Abre o arquivo novamente
          audioFile = SD.open("/audio.wav");
          if (audioFile) {
            audioFile.seek(44); // Pula cabeçalho
            tocandoAudio = true;
            Serial.println("Iniciando áudio...");
          } else {
            Serial.println("ERRO: Não foi possível abrir audio.wav");
          }
        }
      } else {
        Serial.println("Comando 0: Silêncio.");
      }
    } else {
      Serial.print("Erro na requisição HTTP: ");
      Serial.println(httpResponseCode);
    }
    http.end();
  } else {
    Serial.println("WiFi desconectado, tentando reconectar...");
    WiFi.reconnect();
  }
}

// --- SETUP ---
void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("--- Player IoT ESP32-C3 ---");

  // 1. Inicializa WiFi
  conectarWiFi();

  // 2. Inicializa o SPI e o SD
  SPI.begin(SPI_SCK, SPI_MISO, SPI_MOSI);
  if (!SD.begin(SD_CS)) {
    Serial.println("ERRO: Falha ao montar cartão SD!");
    // Não retornamos aqui para permitir debug do WiFi, mas o audio falhará
  } else {
    Serial.println("SD OK.");
  }

  // 3. Configuração do I2S
  i2s_config_t i2s_config = {
    .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_TX),
    .sample_rate = SAMPLE_RATE,
    .bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT,
    .channel_format = I2S_CHANNEL_FMT_RIGHT_LEFT,
    .communication_format = I2S_COMM_FORMAT_STAND_I2S,
    .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
    .dma_buf_count = 4,
    .dma_buf_len = 512,
    .use_apll = false,
    .tx_desc_auto_clear = true,
    .fixed_mclk = 0
  };

  if (i2s_driver_install(I2S_NUM, &i2s_config, 0, NULL) != ESP_OK) {
    Serial.println("Erro ao instalar driver I2S");
    return;
  }

  i2s_pin_config_t pin_config = {
    .bck_io_num = I2S_BCLK,
    .ws_io_num = I2S_LRC,
    .data_out_num = I2S_DOUT,
    .data_in_num = I2S_PIN_NO_CHANGE
  };

  i2s_set_pin(I2S_NUM, &pin_config);
  i2s_zero_dma_buffer(I2S_NUM);
}

// --- LOOP ---
void loop() {
  // Lógica de Prioridade:
  // Se estiver tocando, dedica o processador ao áudio para não picotar.
  // Se não estiver tocando, verifica o tempo para consultar o servidor.

  if (tocandoAudio) {
    if (audioFile && audioFile.available()) {
      int bytesRead = audioFile.read(buffer, sizeof(buffer));
      size_t bytesWritten;
      i2s_write(I2S_NUM, buffer, bytesRead, &bytesWritten, portMAX_DELAY);
    } else {
      // Fim do arquivo
      Serial.println("Fim da reprodução.");
      audioFile.close();
      tocandoAudio = false;
      i2s_zero_dma_buffer(I2S_NUM); // Limpa ruído
      
      // Reseta o timer para não consultar imediatamente após tocar (opcional)
      ultimoCheck = millis(); 
    }
  } else {
    // Verifica se já passou 5 segundos
    if (millis() - ultimoCheck >= intervalo) {
      verificarServidor();
      ultimoCheck = millis();
    }
  }
}