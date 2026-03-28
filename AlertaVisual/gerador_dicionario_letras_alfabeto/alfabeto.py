from PIL import Image, ImageDraw, ImageFont
import numpy as np
import json
import string

coluna_espaco = [[0],
                 [0],
                 [0],
                 [0],
                 [0],
                 [0],
                 [0],
                 [0],
                 [0],
                 [0],
                 [0],
                 [0],
                 [0],
                 [0],
                 [0],
                 [0]
                 ]

def gerar_bitmap(letra, tamanho=16):
    # Cria imagem quadrada preta
    img = Image.new("L", (tamanho, tamanho), 0)
    draw = ImageDraw.Draw(img)

    # Usa fonte padrão do PIL
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 16)

    # Calcula bounding box do texto
    bbox = draw.textbbox((0, 0), letra, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]

    # Centraliza a letra
    x = (tamanho - w) // 2
    y = (tamanho - h-6) // 2

    draw.text((x, y), letra, fill=255, font=font)

    # Converte para matriz 0/1
    matriz = np.array(img) > 128
    return matriz.astype(int).tolist()

#Junta as matrizes
def matrix_union(A, B, C):
    for a, b, c in zip(A, B, C):
        yield [*a, *b, *c]

#Mostra a matriz passando
def mostra_matriz(matriz):
    altura = len(matriz)        # should be 16
    largura = len(matriz[0])    # N (>> 16)

    for inicio in range(largura - 15):  # last window starts at N-16
        janela = []
        for linha in matriz:
            janela.append(linha[inicio:inicio+16])
        yield janela


#Forma a frase
def forma_frase(frase):
    # Start with the first letter (compacted)
    matriz_final = compacta_matriz(alfabeto[frase[0]])

    for i in range(1, len(frase)):
        letra_atual = compacta_matriz(alfabeto[frase[i]])
        # Join: current phrase + space + new letter
        matriz_final = list(matrix_union(matriz_final, coluna_espaco, letra_atual))

    return matriz_final

#Limpa colunas de 0 em matrizes
def compacta_matriz(matriz):
    for coluna in range(0,10):
        num_colunas = len(matriz[0])
        for coluna in range(num_colunas - 1, -1, -1):  # percorre de trás pra frente
            if all(linha[coluna] == 0 for linha in matriz):
                for linha in matriz:
                    del linha[coluna]
    return matriz


# Gera todas as letras maiúsculas
alfabeto = {}
for letra in string.ascii_uppercase:  # A-Z
    alfabeto[letra] = gerar_bitmap(letra)

# Salva em JSON
with open("alfabetoVSCode.json", "w") as f:
    json.dump(alfabeto, f)

print("Arquivo 'alfabetoVSCode.json' gerado com sucesso!")

with open("alfabetoVSCode.json") as f:
    alfabeto = json.load(f)

# Função para imprimir matriz 16x16
def imprimir_matriz(matriz):
    for linha in matriz:
        # converte 0 -> espaço, 1 -> bloco "█" para visual melhor
        print("".join("█" if x else " " for x in linha))

# Escolha a letra que quer testar
letra1 = compacta_matriz(alfabeto["O"])
letra2 = compacta_matriz(alfabeto["I"])

print(f"Matriz da frase compactada:")
#imprimir_matriz(matrix_union(letra1, coluna_espaco, letra2))
imprimir_matriz(forma_frase("CUIDADO"))

for frame in mostra_matriz(forma_frase("CUIDADO")):
    for linha in frame:
        print(linha)
    print("---- next frame ----")
