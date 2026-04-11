#include "Arduino.h"
#include "LoRa_E220.h"
#include <SoftwareSerial.h>
#include <nrf.h>

// =======================================
#define E220_AUX_PIN    D14
#define E220_M0_PIN     D15
#define E220_M1_PIN     D16
#define SENSOR_POWER_PIN D5

#define LORA_ADDRESS_HIGH  0x00
#define LORA_ADDRESS_LOW   0x01
#define DESTINATION_ADDR   0x02
#define LORA_CHANNEL       23
#define LORA_BAUD          9600

#define SENSOR_BAUD        9600
#define NUM_LEITURAS       3
#define SENSOR_TIMEOUT     4000

#define SLEEP_DURATION     10
#define SENSOR_RX_PIN      D9
#define SENSOR_TX_PIN      D21
// =======================================

SoftwareSerial sensorSerial(SENSOR_RX_PIN, SENSOR_TX_PIN);
LoRa_E220 e220ttl(&Serial1, E220_AUX_PIN, E220_M0_PIN, E220_M1_PIN);

unsigned int leituras[NUM_LEITURAS];
unsigned int distanciaMedia = 0;
volatile bool rtc_triggered = false;
int cicloCount = 0;
int enviosComSucesso = 0;
int enviosComFalha = 0;

void setup() {
    pinMode(SENSOR_POWER_PIN, OUTPUT);
    pinMode(E220_M0_PIN, OUTPUT);
    pinMode(E220_M1_PIN, OUTPUT);
    pinMode(E220_AUX_PIN, INPUT);
    
    digitalWrite(SENSOR_POWER_PIN, LOW);
    digitalWrite(E220_M0_PIN, LOW);
    digitalWrite(E220_M1_PIN, LOW);

    Serial.begin(LORA_BAUD);
    while(!Serial);
    delay(2000);
    
    Serial.println("Iniciado");
    Serial.println("===========================================");
    
    // Configura RTC
    NRF_CLOCK->LFCLKSRC = CLOCK_LFCLKSRC_SRC_RC << CLOCK_LFCLKSRC_SRC_Pos;
    NRF_CLOCK->TASKS_LFCLKSTART = 1;
    while (NRF_CLOCK->EVENTS_LFCLKSTARTED == 0);
    NRF_CLOCK->EVENTS_LFCLKSTARTED = 0;
    
    NRF_RTC0->PRESCALER = 1023;
    NRF_RTC0->EVTENSET = RTC_EVTENSET_COMPARE0_Msk; 
    NRF_RTC0->INTENSET = RTC_INTENSET_COMPARE0_Msk; 
    NRF_RTC0->CC[0] = SLEEP_DURATION * 32;
    NVIC_EnableIRQ(RTC0_IRQn);
    NRF_RTC0->TASKS_START = 1;
}

void ligarPerifericos() {
    Serial.println("ligando periféricos...");
    
    // Power cycle completo
    digitalWrite(SENSOR_POWER_PIN, LOW);
    delay(500);
    digitalWrite(SENSOR_POWER_PIN, HIGH);
    delay(1000);
    
    sensorSerial.begin(SENSOR_BAUD);
    Serial1.begin(LORA_BAUD);
    delay(200);
    
    e220ttl.begin();
    delay(800);
    
    Serial.println("periféricos ligados");
}

void desligarPerifericos() {
    Serial.println("desligando periféricos...");
    
    sensorSerial.end();
    Serial1.end();
    digitalWrite(SENSOR_POWER_PIN, LOW);
    delay(200);
    
    Serial.println("periféricos desligados");
}

bool verificarComunicacaoLoRa() {
    Serial.print("verificando comunicação lora... ");
    
    ResponseStructContainer c = e220ttl.getConfiguration();
    if (c.status.code != 1) {
        Serial.print("FALHA - Código: ");
        Serial.println(c.status.code);
        c.close();
        return false;
    }
    
    Configuration config = *(Configuration*) c.data;
    bool configOk = (config.ADDH == LORA_ADDRESS_HIGH) && 
                   (config.ADDL == LORA_ADDRESS_LOW) && 
                   (config.CHAN == LORA_CHANNEL);
    
    c.close();
    
    if (configOk) {
        Serial.println("OK");
        return true;
    } else {
        Serial.println("CONFIG INCORRETA");
        return false;
    }
}

bool configurarLoRa() {
    Serial.println("configurando LoRa...");
    
    digitalWrite(E220_M0_PIN, LOW);
    digitalWrite(E220_M1_PIN, LOW);
    delay(300);
    
    // Primeiro verifica se está comunicando
    if (!verificarComunicacaoLoRa()) {
        Serial.println("lora não está respondendo");
        return false;
    }
    
    // Obtém configuração atual
    ResponseStructContainer c = e220ttl.getConfiguration();
    Configuration config = *(Configuration*) c.data;
    
    // Verifica se precisa reconfigurar
    if (config.ADDH != LORA_ADDRESS_HIGH || config.ADDL != LORA_ADDRESS_LOW || config.CHAN != LORA_CHANNEL) {
        Serial.println("⚙️ Aplicando nova configuração...");
        
        config.ADDH = LORA_ADDRESS_HIGH;
        config.ADDL = LORA_ADDRESS_LOW;
        config.CHAN = LORA_CHANNEL;
        config.TRANSMISSION_MODE.fixedTransmission = FT_FIXED_TRANSMISSION;
        config.SPED.airDataRate = AIR_DATA_RATE_010_24;
        config.OPTION.transmissionPower = POWER_22;
        
        ResponseStatus rs = e220ttl.setConfiguration(config, WRITE_CFG_PWR_DWN_SAVE);
        
        if (rs.code != 1) {
            Serial.println("falha na configuração");
            c.close();
            return false;
        }
        
        Serial.println("configuração aplicada e salva");
        delay(800); // Tempo para salvar na EEPROM
    } else {
        Serial.println("configuração já está correta");
    }
    
    c.close();
    return true;
}

bool aguardarLoRaPronto() {
    Serial.print("aguardando lora ficar pronto... ");
    
    unsigned long startTime = millis();
    while (digitalRead(E220_AUX_PIN) == LOW) {
        if (millis() - startTime > 10000) {
            Serial.println("TIMEOUT");
            return false;
        }
        delay(100);
    }
    
    Serial.println("PRONTO");
    return true;
}

bool lerSensor() {
    Serial.println("lendo sensor...");
    
    int leiturasColetadas = 0;
    unsigned long startTime = millis();
    byte frame[4];
    byte frameIndex = 0;
    
    // Limpa buffer
    while(sensorSerial.available()) {
        sensorSerial.read();
    }
    
    while(leiturasColetadas < NUM_LEITURAS && (millis() - startTime < SENSOR_TIMEOUT)) {
        if(sensorSerial.available()) {
            byte byteLido = sensorSerial.read();
            
            if(frameIndex == 0 && byteLido == 0xFF) {
                frame[frameIndex++] = byteLido;
            }
            else if(frameIndex > 0 && frameIndex < 4) {
                frame[frameIndex++] = byteLido;
                
                if(frameIndex == 4) {
                    if(frame[0] == 0xFF) {
                        byte checksum = (0xFF + frame[1] + frame[2]) & 0xFF;
                        if(checksum == frame[3]) {
                            unsigned int distancia = (frame[1] << 8) | frame[2];
                            leituras[leiturasColetadas] = distancia;
                            leiturasColetadas++;
                            
                            Serial.print(" leitura ");
                            Serial.print(leiturasColetadas);
                            Serial.print(": ");
                            Serial.print(distancia);
                            Serial.println(" mm");
                        }
                    }
                    frameIndex = 0;
                }
            } else {
                frameIndex = 0;
            }
        }
        delay(5);
    }
    
    if(leiturasColetadas >= 2) {
        unsigned long soma = 0;
        for(int i = 0; i < leiturasColetadas; i++) {
            soma += leituras[i];
        }
        distanciaMedia = soma / leiturasColetadas;
        
        Serial.print("media (");
        Serial.print(leiturasColetadas);
        Serial.print("/");
        Serial.print(NUM_LEITURAS);
        Serial.print(" leituras): ");
        Serial.print(distanciaMedia);
        Serial.println(" mm");
        return true;
    } else {
        Serial.println("Falha na leitura do sensor");
        distanciaMedia = 1500 + (cicloCount % 500); // Valor de fallback
        return false;
    }
}

bool enviarDadosLoRa() {
    Serial.println("iniciando processo de envio...");
    
    // Verificação 1: LoRa está configurado?
    if (!verificarComunicacaoLoRa()) {
        Serial.println("VERIFICAÇÃO 1 FALHOU: LoRa não responde");
        return false;
    }
    
    // Verificação 2: LoRa está pronto para transmitir?
    if (!aguardarLoRaPronto()) {
        Serial.println("VERIFICAÇÃO 2 FALHOU: LoRa não ficou pronto");
        return false;
    }
    
    // Prepara mensagem
    char mensagem[100];
    sprintf(mensagem, "{\"id\":\"n01\",\"tp\":\"u\",\"dt\":{\"Q\":0,\"I\":0,\"N\":%d}}", distanciaMedia);
    
    Serial.print("Tentando enviar: ");
    Serial.println(mensagem);
    
    // Envia mensagem
    ResponseStatus status = e220ttl.sendFixedMessage(0, DESTINATION_ADDR, LORA_CHANNEL, mensagem);
    
    Serial.print("Status do envio: ");
    Serial.print(status.getResponseDescription());
    Serial.print(" (Código: ");
    Serial.print(status.code);
    Serial.println(")");
    
    if(status.code != 1) {
        Serial.println("ENVIO FALHOU: Código de erro");
        return false;
    }
    
    // Verificação 3: Aguarda confirmação de transmissão
    Serial.print("Aguardando confirmação de transmissão... ");
    unsigned long waitStart = millis();
    bool transmissaoCompleta = false;
    
    while(millis() - waitStart < 5000) {
        if(digitalRead(E220_AUX_PIN) == LOW) {
            transmissaoCompleta = true;
            break;
        }
        delay(50);
    }
    
    if(transmissaoCompleta) {
        Serial.println("CONFIRMADA");
        enviosComSucesso++;
        return true;
    } else {
        Serial.println("NÃO CONFIRMADA");
        return false;
    }
}

void entrarRepouso() {
    Serial.println("entrando em repouso...");
    Serial.flush();
    delay(200);
    
    rtc_triggered = false;
    NRF_RTC0->EVENTS_COMPARE[0] = 0;
    NRF_RTC0->TASKS_CLEAR = 1;
    NRF_RTC0->CC[0] = SLEEP_DURATION * 32;
    
    Serial.end();
    SCB->SCR |= SCB_SCR_SLEEPDEEP_Msk;
    
    while(!rtc_triggered) {
        __WFE();
        __SEV();
        __WFE();
    }
    
    Serial.begin(LORA_BAUD);
    Serial.println("acordou do repouso");
}

extern "C" void RTC0_IRQHandler(void) {
    if(NRF_RTC0->EVENTS_COMPARE[0]) {
        NRF_RTC0->EVENTS_COMPARE[0] = 0;
        rtc_triggered = true;
    }
}

void loop() {
    cicloCount++;
    
    Serial.println("\n=================================");
    Serial.print("CICLO #");
    Serial.println(cicloCount);
    Serial.print("ESTATÍSTICAS: ");
    Serial.print(enviosComSucesso);
    Serial.print(" sucessos / ");
    Serial.print(enviosComFalha);
    Serial.println(" falhas");
    
    // 1. Liga periféricos
    ligarPerifericos();
    
    // 2. Configura LoRa
    bool loraConfigurado = configurarLoRa();
    
    // 3. Lê sensor
    bool sensorLido = lerSensor();
    
    // 4. Tenta enviar apenas se ambos estão OK
    bool envioBemSucedido = false;
    
    if(loraConfigurado && sensorLido) {
        envioBemSucedido = enviarDadosLoRa();
    } else {
        Serial.println("Condições não atendidas para envio");
        if(!loraConfigurado) Serial.println("  - LoRa não configurado");
        if(!sensorLido) Serial.println("  - Sensor não leu");
    }
    
    if(envioBemSucedido) {
        Serial.println("ENVIO BEM SUCEDIDO CONFIRMADO");
    } else {
        enviosComFalha++;
        Serial.println("FALHA NO ENVIO");
    }
    
    // 5. Pequena pausa
    delay(1000);
    
    // 6. Desliga periféricos
    desligarPerifericos();
    
    // 7. Repouso
    entrarRepouso();
}
