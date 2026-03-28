#include "Arduino.h"
#include "LoRa_E220.h"

// ================= CONFIGURAÇÕES =================
#define E220_RX_PIN  1
#define E220_TX_PIN  0
#define E220_AUX_PIN 14
#define E220_M0_PIN  15
#define E220_M1_PIN  16

#define mos1 8
#define mos2 7

// Endereço do transmissor
#define LORA_ADDRESS_HIGH 0x00
#define LORA_ADDRESS_LOW  0x01

// Endereço do receptor
#define DESTINATION_ADDL  0x02

// Canal
#define LORA_CHANNEL 23

// Mensagem
const char* MENSAGEM = "{\"id\": \"nivel1\", \"valor\": 15}";

// Intervalo
#define TRANSMISSION_INTERVAL 5000
// ==================================================

LoRa_E220 e220ttl(E220_RX_PIN, E220_TX_PIN, E220_AUX_PIN, E220_M0_PIN, E220_M1_PIN);

void setup() {
  Serial.begin(9600);
  while (!Serial) {}
  delay(500);

  pinMode(mos1, OUTPUT);
  pinMode(mos2, OUTPUT);
  digitalWrite(mos1, 1);
  digitalWrite(mos2, 1);

  Serial.println("Iniciando transmissor LoRa...");

  e220ttl.begin();

  ResponseStructContainer c = e220ttl.getConfiguration();
  Configuration configuration = *(Configuration*)c.data; // CORRIGIDO

  configuration.ADDH = LORA_ADDRESS_HIGH;
  configuration.ADDL = LORA_ADDRESS_LOW;
  configuration.CHAN = LORA_CHANNEL;

  configuration.SPED.uartBaudRate = UART_BPS_9600;
  configuration.SPED.airDataRate  = AIR_DATA_RATE_010_24;
  configuration.SPED.uartParity   = MODE_00_8N1;

  configuration.OPTION.subPacketSetting = SPS_200_00;
  configuration.OPTION.RSSIAmbientNoise = RSSI_AMBIENT_NOISE_DISABLED;
  configuration.OPTION.transmissionPower = POWER_22;

  configuration.TRANSMISSION_MODE.enableRSSI = RSSI_DISABLED;
  configuration.TRANSMISSION_MODE.fixedTransmission = FT_FIXED_TRANSMISSION;
  configuration.TRANSMISSION_MODE.enableLBT = LBT_DISABLED;
  configuration.TRANSMISSION_MODE.WORPeriod = WOR_2000_011;

  ResponseStatus code = e220ttl.setConfiguration(configuration, WRITE_CFG_PWR_DWN_SAVE);
  Serial.print("Configuracao aplicada: ");
  Serial.println(code.getResponseDescription());
  c.close();

  Serial.println("Transmissor LoRa pronto!");
}

void loop() {
  ResponseStatus code = e220ttl.sendFixedMessage(0, DESTINATION_ADDL, LORA_CHANNEL, MENSAGEM);
  Serial.print("Enviando mensagem: ");
  Serial.println(MENSAGEM);
  Serial.print("Status: ");
  Serial.println(code.getResponseDescription());
  delay(TRANSMISSION_INTERVAL);
}


void printParameters(struct Configuration configuration) {
  Serial.println("----------------------------------------");

  Serial.print(F("HEAD : "));  Serial.print(configuration.COMMAND, HEX);Serial.print(" ");Serial.print(configuration.STARTING_ADDRESS, HEX);Serial.print(" ");Serial.println(configuration.LENGHT, HEX);
  Serial.println(F(" "));
  Serial.print(F("AddH : "));  Serial.println(configuration.ADDH, HEX);
  Serial.print(F("AddL : "));  Serial.println(configuration.ADDL, HEX);
  Serial.println(F(" "));
  Serial.print(F("Chan : "));  Serial.print(configuration.CHAN, DEC); Serial.print(" -> "); Serial.println(configuration.getChannelDescription());
  Serial.println(F(" "));
  Serial.print(F("SpeedParityBit     : "));  Serial.print(configuration.SPED.uartParity, BIN);Serial.print(" -> "); Serial.println(configuration.SPED.getUARTParityDescription());
  Serial.print(F("SpeedUARTDatte     : "));  Serial.print(configuration.SPED.uartBaudRate, BIN);Serial.print(" -> "); Serial.println(configuration.SPED.getUARTBaudRateDescription());
  Serial.print(F("SpeedAirDataRate   : "));  Serial.print(configuration.SPED.airDataRate, BIN);Serial.print(" -> "); Serial.println(configuration.SPED.getAirDataRateDescription());
  Serial.println(F(" "));
  Serial.print(F("OptionSubPacketSett: "));  Serial.print(configuration.OPTION.subPacketSetting, BIN);Serial.print(" -> "); Serial.println(configuration.OPTION.getSubPacketSetting());
  Serial.print(F("OptionTranPower    : "));  Serial.print(configuration.OPTION.transmissionPower, BIN);Serial.print(" -> "); Serial.println(configuration.OPTION.getTransmissionPowerDescription());
  Serial.print(F("OptionRSSIAmbientNo: "));  Serial.print(configuration.OPTION.RSSIAmbientNoise, BIN);Serial.print(" -> "); Serial.println(configuration.OPTION.getRSSIAmbientNoiseEnable());
  Serial.println(F(" "));
  Serial.print(F("TransModeWORPeriod : "));  Serial.print(configuration.TRANSMISSION_MODE.WORPeriod, BIN);Serial.print(" -> "); Serial.println(configuration.TRANSMISSION_MODE.getWORPeriodByParamsDescription());
  Serial.print(F("TransModeEnableLBT : "));  Serial.print(configuration.TRANSMISSION_MODE.enableLBT, BIN);Serial.print(" -> "); Serial.println(configuration.TRANSMISSION_MODE.getLBTEnableByteDescription());
  Serial.print(F("TransModeEnableRSSI: "));  Serial.print(configuration.TRANSMISSION_MODE.enableRSSI, BIN);Serial.print(" -> "); Serial.println(configuration.TRANSMISSION_MODE.getRSSIEnableByteDescription());
  Serial.print(F("TransModeFixedTrans: "));  Serial.print(configuration.TRANSMISSION_MODE.fixedTransmission, BIN);Serial.print(" -> "); Serial.println(configuration.TRANSMISSION_MODE.getFixedTransmissionDescription());

  Serial.println("----------------------------------------");
}