# Importações
from machine import Pin
import machine
import neopixel
import ujson
import network
import time
import urequests
import gc

# --- Configurações de Rede e URL ---
url = "http://192.168.137.1:9000/sensores/alerta/mensagem"
SSID = 'WiFi Notebook'
PASSWORD = 'senha123'

# --- Configurações do Display NeoPixel ---
NUM_LEDS = 256
PIN = 4 # Pino GPIO ao qual o NeoPixel está conectado

displayXSize = 16
displayYSize = 16

# VARIÁVEL GLOBAL DE COR: Será alterada no loop principal
cor = (50,0,0) # Cor inicial (vermelho escuro)

# --- Carregamento de Dados ---
try:
    with open("alfabetoVersao2.json", 'r') as f:
        alfabeto = ujson.load(f)
        
    with open("animacaoInundacao.json", 'r') as f:
        inundacao = ujson.load(f)
except OSError as e:
    print(f"Erro ao carregar arquivos JSON: {e}")
    # Tratamento de erro ou reinicialização aqui

# --- Matrizes de Suporte (Inalteradas) ---
coluna_espaco = [[0], [0], [0], [0], [0], [0], [0], [0], 
                 [0], [0], [0], [0], [0], [0], [0], [0]]

comeco_animacao_placa = [
 [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
 [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,0,0],
 [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,1,0,0,1,0],
 [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,1,1,1,1,0,1],
 [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,1,1,0,0,1],
 [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,1,0,0,0,1],
 [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,1,1,0,0,0,1],
 [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,1,0,1,0,0,0,1],
 [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,1,0,0,1,0],
 [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,0,0],
 [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0],
 [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0],
 [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0],
 [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0],
 [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0],
 [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0]]

# --- Funções Auxiliares (Mesmas da versão otimizada) ---

def connect_wifi(ssid, password, timeout=15):
    sta = network.WLAN(network.STA_IF)
    if sta.active():
        sta.active(False)
        time.sleep(0.5)
    sta.active(True)
    if sta.isconnected():
        sta.disconnect()
        time.sleep(1)
    t = 0
    while not sta.isconnected() and t < timeout:
        print(f"Conectando... (Tentativa {t+1}/{timeout})")
        try:
            sta.connect(ssid, password) 
        except Exception as e:
            print(f"Erro ao tentar conectar: {e}")
        time.sleep(2)
        t += 1
    if sta.isconnected():
        print("Conectado! IP:", sta.ifconfig()[0])
        return True
    else:
        print("Falha ao conectar")
        print("Status: ", sta.status())
        return False

def compacta_matriz(matriz):
    num_colunas = len(matriz[0])
    for coluna in range(num_colunas - 1, -1, -1):
        if all(linha[coluna] == 0 for linha in matriz):
            for linha in matriz:
                del linha[coluna]
    return matriz

def mostra_matriz(matriz):
    largura = len(matriz[0])    
    if largura > 16:
        limite = largura - 16
    else:
        limite = 0
    
    for inicio in range(limite + 1): 
        janela = []
        for linha in matriz:
            janela.append(linha[inicio:inicio+16])
        yield janela

def forma_frase(frase):
    # Cópia rasa dos caracteres para evitar corromper o 'alfabeto'
    matriz_final = compacta_matriz([linha[:] for linha in alfabeto[frase[0]]]) 

    for i in range(1, len(frase)):
        letra_atual = compacta_matriz([linha[:] for linha in alfabeto[frase[i]]])
        matriz_final = list(matrix_union(matriz_final, coluna_espaco, letra_atual))

    return matriz_final

def matrix_union(A, B, C):
    for a, b, c in zip(A, B, C):
        yield a + b + c

displayBuffer = []
for y in range(displayYSize):
        displayBuffer.append([0] * displayXSize)
        
def clearDisplayBuffer():
    for y in range(displayYSize):
        for x in range(displayXSize):
            displayBuffer[y][x]=0
            
def drawMatrix(x1, y1, matrix, inMatrix):
    for y in range(len(matrix)):
        for x in range(len(matrix[0])):
            if x + x1 < displayXSize and y + y1 < displayYSize:
                if matrix[y][x] == 1:
                    inMatrix[y + y1][x + x1] = 1 

# np_global deve ser passado como argumento
def displayPrint(np_obj, img, col):
    """Desenha o frame e escreve no objeto NeoPixel reutilizado."""
    global cor # Declara que estamos usando a variável global 'cor'
    
    clearDisplayBuffer()
    
    drawMatrix(col , 0, img, displayBuffer)
    
    for y in range(16):
        for x in range(16):
            if y % 2 == 1:
                c = x + 16*y
            if y % 2 == 0:
                c = 15 - x + 16*y
                
            if displayBuffer[y][x] == 1:
                np_obj[c] = cor # Usa a cor global atual
            else:
                np_obj[c] = (0, 0, 0) 
                
    np_obj.write()

# --- Pré-inicialização ---
gc.collect()

# OTIMIZAÇÃO CRÍTICA: Inicializa o NeoPixel uma única vez
np_global = neopixel.NeoPixel(machine.Pin(PIN), NUM_LEDS)

# Conecta ao Wi-Fi
if not connect_wifi(SSID, PASSWORD):
    print("O ESP32 será reiniciado em 5 segundos devido à falha de Wi-Fi.")
    time.sleep(5)
    machine.reset()

mensagemServer = "AAA" # Valor inicial

# --- Loop Principal com Lógica Condicional ---
while True:
    
    # === Lógica de Estado e Cor ===
    
    # 1. Verifica se a mensagem contém as palavras-chave (case-insensitive)
    mensagem_upper = mensagemServer.upper() 
    is_alert = "ENCHENTE" in mensagem_upper or "INUNDACAO" in mensagem_upper
    
    # 2. Define a cor global
    if is_alert:
        # Estado de Alerta: Vermelho forte (R, G, B)
        cor = (50, 0, 0) 
        print("Estado: ALERTA (Cor: Vermelho)")
    else:
        # Estado Normal: Verde
        cor = (0, 50, 0) 
        print("Estado: NORMAL (Cor: Verde)")

    # === 1. Exibe a Mensagem Rolante (Com a cor definida) ===
    mensagem_completa = "|||||||||||||||||" + mensagemServer + "||||||||||||||||"
    matriz_rolagem = forma_frase(mensagem_completa)
    
    for frame in mostra_matriz(matriz_rolagem):
        displayPrint(np_global, frame, 0)
        time.sleep_ms(35)
        
    del matriz_rolagem # Libera a matriz
    gc.collect()

    # === 2. Animações Condicionais ===
    if is_alert:
        print("Exibindo animação de inundação.")
        
        # Animação da placa de início
        for frame in mostra_matriz(comeco_animacao_placa):
            displayPrint(np_global, frame, 0)
            time.sleep_ms(35)
            
        time.sleep_ms(350)
        
        # Animação de inundação (frames fixos)
        for char in "1234567890ABCDEFGHIJKLMNOPQRSTU":
            try:
                displayPrint(np_global, inundacao[char], 0)
            except KeyError:
                print(f"Aviso: Caractere '{char}' não encontrado em animacaoInundacao.json")
            time.sleep_ms(450)
    else:
        # Se não for alerta, aguarda antes de buscar a nova mensagem
        print("Nenhuma palavra-chave encontrada. Aguardando...")
        time.sleep(2) 
    
    # === 3. Requisição HTTP e Coleta de Lixo ===
    gc.collect()
    try:
        resposta = urequests.get(url, timeout=5)
        if resposta.status_code == 200:
            mensagemServer = resposta.text.strip()
            print("Conteúdo recebido:", mensagemServer)
        else:
            print(f"Erro HTTP: {resposta.status_code}")
        
        resposta.close() 
        
    except Exception as e:
        print("Erro na requisição:", e)
        
    gc.collect()
    # Para monitoramento:
    print("Memória livre após requisição:", gc.mem_free())