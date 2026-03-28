#import serial
#import json
#import requests
#
#ser = serial.Serial('COM10', 9600)  # Porta onde o microcontrolador está conectado
#url = "http://localhost:9000/nivel"  # endpoint do Horse
#
##data = {
##  " firstName " : "John" ,
##  " sobrenome " : "Doe" ,
##  " idade " : 21
##}
#
##response = requests.post(url, json=data)
##print(response.text)
#
#
#while True:
#    line = ser.readline().decode('utf-8').strip()
#    #try:
#        #data = json.loads(line)  # tenta interpretar o JSON recebido
#    response = requests.post(url, data=line)
#    print(f"Enviado: {line} | Resposta: {response.text}")
#    #except json.JSONDecodeError:
#        #print("Erro ao decodificar JSON:", line)

import serial
import requests
import json

ser = serial.Serial('COM17', 9600)  # Porta do microcontrolador
url = "http://localhost:9000/sensores"

print("Lendo dados da serial e enviando ao servidor...")

while True:
    line = ser.readline().decode('utf-8').strip()
    print(line)
    if line:
        try:
            data = json.loads(line)  # converte string JSON → dicionário
            response = requests.post(url, json=data)
            #print(line)
            print(response.text)
        except json.JSONDecodeError as e:
            print(f"Erro ao decodificar JSON: {e}")
        except Exception as e:
            print(line)
            print(f"Erro ao enviar dados: {e}")