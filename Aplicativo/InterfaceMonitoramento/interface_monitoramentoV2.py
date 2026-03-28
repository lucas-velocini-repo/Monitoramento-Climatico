import streamlit as st
from streamlit_autorefresh import st_autorefresh
import requests
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
import os

# --- Configuração da página -----------------------------------------------
st.set_page_config(layout="wide", page_title="Monitoramento de Rios")
st_autorefresh(interval=5000, key="auto-refresh")

#---------------------------------------------------------------------------

# --- CSS e título ---------------------------------------------------------
base_logo_path = os.path.dirname(os.path.abspath(__file__))
logo_path = os.path.join(base_logo_path, "imgs", "logo.png")

st.markdown("""
    <style>
        h1 { margin-bottom: 0 !important; padding-bottom: 0 !important; }
        hr { margin-top: 0.3rem !important; }
    </style>
""", unsafe_allow_html=True)

col1, col2 = st.columns([10, 1])
with col2:
    st.image(logo_path, width=180)
with col1:
    st.markdown(
        """
        <h1 style="color:white; margin-bottom:0; font-size:36px;">
            <span style="color:#bd26a1;">Pink Fluidos - </span>Sistema de Monitoramento de Rios e Alerta Preventivo
        </h1>
        """,
        unsafe_allow_html=True
    )

st.markdown("<hr style='margin-top:5px;'>", unsafe_allow_html=True)

#-------------------------------------------------------------------------------

# --- Buscar módulos do servidor -----------------------------------------------
url = "http://localhost:9000/sensores/listar/todos"
try:
    response = requests.get(url, timeout=5)
    response.raise_for_status()
    modules = response.json()
except requests.RequestException as e:
    st.error(f"Erro ao buscar dados do servidor: {e}")
    modules = []

#--------------------------------------------------------------------------------

# --- Buscar dados de chuva do servidor -----------------------------------------
def buscar_dados_chuva(id):
    url = f"http://localhost:9000/sensores/dados/pluv/{id}"

    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        dados = response.json()  # <-- lista completa do servidor

        # Converte para DataFrame diretamente
        df = pd.DataFrame(dados)

        # Renomeia colunas para exibição
        df = df.rename(columns={
            "timestamp": "Horário (dia)",
            "rainMm": "Quantidade de chuva (mm)"
        })

        # Armazena no session_state substituindo o conteúdo anterior
        st.session_state["dados_chuva"] = df

        return df

    except requests.RequestException as e:
        st.error(f"Erro ao buscar dados do servidor: {e}")
        return pd.DataFrame()


#--------------------------------------------------------------------------------

# --- Buscar dados de nível do servidor -----------------------------------------
def buscar_dados_nivel(id):
    url = f"http://localhost:9000/sensores/dados/nivel/{id}"

    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        dados = response.json()  # <-- lista completa do servidor

        # Converte para DataFrame diretamente
        df = pd.DataFrame(dados)

        # Renomeia colunas para exibição
        df = df.rename(columns={
            "timestamp": "Horário (dia)",
            "waterLevelCm": "Nível da água (m)"
        })

        # Armazena no session_state substituindo o conteúdo anterior
        st.session_state["dados_nivel"] = df

        return df

    except requests.RequestException as e:
        st.error(f"Erro ao buscar dados do servidor: {e}")
        return pd.DataFrame()

#--------------------------------------------------------------------------------

# --- Lógica do sistema de alerta -----------------------------------------------

# --- Funções --------------------------------

def obter_dados_meteorologicos(lat, lon):
    #"""
    #Busca dados de chuva atual e previsão imediata.
    #Retorna a intensidade da chuva em mm/h prevista pela API.
    #"""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "rain,weather_code",
        "hourly": "rain",
        "forecast_days": 1
    }
    try:
        r = requests.get(url, params=params, timeout=5)
        r.raise_for_status()
        data = r.json()
        # Retorna a chuva atual (mm) reportada pela API
        return data.get("current", {}).get("rain", 0.0)
    except Exception as e:
        print(f"Erro API Meteo: {e}")
        return 0.0 # Retorna 0 em caso de erro para não quebrar a lógica

def calcular_nivel_risco(
    nivel_rio_atual, 
    nivel_critico, 
    intensidade_pluviometro, 
    lat=-22.90, lon=-47.06, # Coordenadas padrão (ex: Campinas)
    limite_chuva_leve=2.0,
    limite_chuva_moderada=10.0,
    limite_chuva_forte=30.0
):
    #"""
    #Retorna: (nivel_alerta (int), mensagem_painel (str), alerta_sonoro (str))
    #"""
    
    # 1. Busca dados da API
    #chuva_api = obter_dados_meteorologicos(lat, lon)
    chuva_api = 0
    
    # 2. Unifica a intensidade da chuva (Considera o maior valor entre o sensor local e a API)
    # Isso garante segurança: se a API diz que chove e o sensor falha (ou vice-versa), assumimos chuva.
    intensidade_chuva = max(intensidade_pluviometro, chuva_api)

    # Definição de estados baseados no nível do rio relativo ao crítico
    pct_nivel = nivel_rio_atual / nivel_critico if nivel_critico > 0 else 0
    
    nivel_rio_baixo = 0.40 <= pct_nivel < 0.60
    nivel_rio_medio = 0.60 <= pct_nivel < 0.85
    nivel_rio_alto  = 0.85 <= pct_nivel < 1.0
    nivel_transbordou = pct_nivel >= 1.0

    # --- LÓGICA DOS NÍVEIS (Ordem decrescente de prioridade) ---

    # NÍVEL 4: Emergência
    if nivel_transbordou:
        return 4, "Inundacao", "Ligado"

    # NÍVEL 3: Risco Alto
    # Chuva forte (local ou API) E (Rio alto OU previsão de ultrapassar crítico*)
    # *Simplificação: Se já está alto (90%) e chovendo forte, o risco é alto.
    if (intensidade_chuva >= limite_chuva_forte) or (nivel_rio_alto):
        return 3, "Critico", "Desligado"

    # NÍVEL 2: Risco Moderado
    # Chuva moderada E Nivel entre X e Y (Médio)
    if (intensidade_chuva >= limite_chuva_moderada) or (nivel_rio_medio):
        return 2, "Subindo", "Desligado"

    # NÍVEL 1: Risco Leve
    # Chuva fraca E Nivel baixo
    if (intensidade_chuva > 0) or (nivel_rio_baixo): 
        return 1, "Baixo", "Desligado"

    # NÍVEL 0: Seguro
    return 0, "Seguro", "Desligado"

# --- Controles de Parametrização (Sidebar para não poluir) ---
st.sidebar.header("Parâmetros de Alerta")

# Controle do Nível Crítico Global (ou pegue do sensor específico selecionado na lógica abaixo)
param_nivel_critico = st.sidebar.number_input("Nível Crítico do Rio (m)", value=2.5, step=0.1)
param_altura_sensor = st.sidebar.number_input("Altura do sensor de nível (m)", value=0.4, step=0.05)

# Controle de Intensidade de Chuva
st.sidebar.subheader("Limiares de Chuva (mm/h)")
param_chuva_leve = st.sidebar.number_input("Limite Chuva Leve", value=2.0)
param_chuva_mod  = st.sidebar.number_input("Limite Chuva Moderada", value=10.0)
param_chuva_forte = st.sidebar.number_input("Limite Chuva Forte", value=30.0)

# Coordenadas para API (pode fixar se quiser)
lat_local = -22.90
lon_local = -47.06

# --- Simulação/Leitura dos dados atuais para o cálculo ---
# OBS: No sistema real, você pegaria o ÚLTIMO valor do dataframe 'st.session_state["dados_nivel"]'
# e 'st.session_state["dados_chuva"]'. Vou fazer um mock seguro aqui:

# Tenta pegar valor real do nível
nivel_atual = 0.0
nivel_real = 0.0
if "dados_nivel" in st.session_state and not st.session_state["dados_nivel"].empty:
    # Pega o último valor registrado
    col_nivel = "Nível da água (m)" if "Nível da água (m)" in st.session_state["dados_nivel"] else "waterLevelCm"
    val = st.session_state["dados_nivel"].iloc[-1][col_nivel]
    nivel_atual = val if col_nivel == "Nível da água (m)" else val / 100
    nivel_real = param_nivel_critico - (nivel_atual - param_altura_sensor)

# Tenta pegar valor real da chuva (intensidade do último registro)
chuva_atual_sensor = 0.0
if "dados_chuva" in st.session_state and not st.session_state["dados_chuva"].empty:
    # Assume que calculou intensidade no bloco do pluviometro ou pega o último acumulado
    # Simplificando pegando o último rainMm puro como intensidade instantânea
    chuva_atual_sensor = st.session_state["dados_chuva"].iloc[-1]["Quantity de chuva (mm)"] if "Quantity de chuva (mm)" in st.session_state["dados_chuva"] else 0.0

# --- CÁLCULO DO ESTADO ---
nivel_calc, msg_calc, som_calc = calcular_nivel_risco(
    nivel_rio_atual=nivel_real,
    nivel_critico=param_nivel_critico,
    intensidade_pluviometro=chuva_atual_sensor,
    lat=lat_local,
    lon=lon_local,
    limite_chuva_leve=param_chuva_leve,
    limite_chuva_moderada=param_chuva_mod,
    limite_chuva_forte=param_chuva_forte
)

# --- Lógica de Histerese (Emergência Nível 4) ---
if "estado_emergencia_timestamp" not in st.session_state:
    st.session_state.estado_emergencia_timestamp = None

# Se calculou nível 4, marca o tempo
if nivel_calc == 4:
    if st.session_state.estado_emergencia_timestamp is None:
        st.session_state.estado_emergencia_timestamp = datetime.now()
    
    # Mantém o estado calculado
    estado_final = 4
    msg_final = "Inundacao"
    som_final = "Ligado"

else:
    # Se calculou menos que 4, mas estava em emergência, verifica o tempo
    if st.session_state.estado_emergencia_timestamp is not None:
        tempo_passado = datetime.now() - st.session_state.estado_emergencia_timestamp
        # Exemplo: obriga a ficar 30 minutos em alerta mesmo se a água baixar rápido
        if tempo_passado < timedelta(minutes=1):
            estado_final = 4
            msg_final = "Inundacao diminuindo"
            som_final = "Ligado"
        else:
            # Saiu do tempo de segurança
            st.session_state.estado_emergencia_timestamp = None
            estado_final = nivel_calc
            msg_final = msg_calc
            som_final = som_calc
    else:
        estado_final = nivel_calc
        msg_final = msg_calc
        som_final = som_calc

# --- EXIBIÇÃO NO TOPO DA PÁGINA (DASHBOARD) ---
cor_fundo = {
    0: "#28a745", # Verde
    1: "#17a2b8", # Azul
    2: "#ffc107", # Amarelo
    3: "#fd7e14", # Laranja
    4: "#dc3545"  # Vermelho
}

# Envia comando para o hardware (opcional, se quiser automatizar)
# if som_final == "Ligado":
#    requests.post("http://localhost:9000/sensores/alerta/beepsonoro", data="1")

# -------------------------------------------------------------------------------

# --- Mapeamentos ---------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(BASE_DIR, "imgs")

type_names = {
    "a": "Som", 
    "m": "LED", 
    "b": "Pluv", 
    "u": "Nível"
}
prefix_titles = {
    "b": "Alerta Sonoro", 
    "n": "Sensor de Nível", 
    "p": "Pluviômetro", 
    "v": "Alerta Visual"
}

image_paths = {
    "b": os.path.join(IMG_DIR, "speaker-w.png"),
    "n": os.path.join(IMG_DIR, "ultrassonic-sensor-w.png"),
    "p": os.path.join(IMG_DIR, "rain-gauge2-w.png"),
    "v": os.path.join(IMG_DIR, "led2-w.png")
}

#-------------------------------------------------------------------

#------ inicializa session_state se necessário ---------------------
if "selected_filter" not in st.session_state:
    st.session_state.selected_filter = "todos"
if "selected_module" not in st.session_state:
    st.session_state.selected_module = None
if "dados_chuva" not in st.session_state:
    st.session_state["dados_chuva"] = pd.DataFrame()
if "dados_nivel" not in st.session_state:
    st.session_state["dados_nivel"] = pd.DataFrame()    

#-------------------------------------------------------------------

#=================== Interface principal ===========================
if not modules:
    st.warning("Nenhum módulo encontrado no servidor.")
else:
    col1, col2 = st.columns([2, 1], gap="large")

# --- Coluna direita: lista e filtros ------------------------------
    with col2:
        st.subheader("Módulos disponíveis")

        device_types = sorted(list(set([m["deviceType"] for m in modules])))
        # botões de filtro (mantendo visual de botões)
        cols = st.columns(len(device_types) + 1)
        if cols[0].button("Todos", use_container_width=True):
            st.session_state.selected_filter = "todos"

        for i, dtype in enumerate(device_types):
            label = type_names.get(dtype.lower(), dtype.upper())
            if cols[i + 1].button(label, use_container_width=True):
                st.session_state.selected_filter = dtype

        # Filtrar lista (não altera selected_module)
        if st.session_state.selected_filter == "todos":
            filtered_modules = modules
        else:
            filtered_modules = [m for m in modules if m["deviceType"] == st.session_state.selected_filter]

        if not filtered_modules:
            st.warning("Nenhum módulo encontrado para esse tipo.")
        else:
            for module in filtered_modules:
                device_id = module["deviceId"]
                description = module["description"]

                prefix = device_id[0].lower()
                title_prefix = prefix_titles.get(prefix, "Módulo")
                title = f"{title_prefix} {device_id[-2:]}"

                # container visual (usa border True do Streamlit)
                with st.container(border=True):
                    col_img, col_text = st.columns([1, 3])
                    with col_img:
                        img_path = image_paths.get(prefix, os.path.join(IMG_DIR, "default.png"))
                        # se imagem não existir, evita crash mostrando nada
                        if os.path.exists(img_path):
                            st.image(img_path, width=50)
                    with col_text:
                        st.markdown(f"### {title}")
                        st.markdown(f"<small>{description}</small>", unsafe_allow_html=True)

                    # botão que seleciona o módulo (apenas isso atualiza o painel esquerdo)
                    if st.button("Ver detalhes", key=f"btn_{device_id}", use_container_width=False):
                        st.session_state.selected_module = device_id

# ----------------------------------------------------------------------------------------------------

# --- Coluna esquerda: painel de detalhes (somente atualiza quando selected_module muda) -------------
    with col1:
        selected_id = st.session_state.get("selected_module", None)
        if selected_id:
            # procura o módulo no conjunto completo (não no filtered_modules)
            selected_module = next((m for m in modules if m["deviceId"] == selected_id), None)
            if selected_module:
                prefix = selected_module["deviceId"][0].lower()
                dtype = selected_module["deviceType"].lower()
                device_name = type_names.get(dtype, dtype.upper())
                device_title = prefix_titles.get(prefix, dtype.upper())
                device_number = selected_module["deviceId"][-2:]

                # Cabeçalho (isso é estático e não perde estado)
                st.subheader(f"Detalhes do {device_title.lower()} {device_number}")
                st.markdown(f"**Localização:** {selected_module['description']}")
                st.markdown(f"**Tipo:** {device_name.capitalize()}")
                st.markdown("**Status:** Ativo")
                st.markdown("<hr style='margin-top:5px;'>", unsafe_allow_html=True)

                # --- Conteúdo específico por prefix ------------------------------------------------------
                
                # Pluviômetro -----------------------------------------------------------------------------
                if prefix == "p":  
                    df = buscar_dados_chuva(selected_id)

                    if not df.empty:
                        df["Horário (dia)"] = pd.to_datetime(df["Horário (dia)"])
                        df["Data"] = df["Horário (dia)"].dt.date

                        dias_disponiveis = sorted(df["Data"].unique())
                        selected_day = st.date_input("Selecione o dia:", dias_disponiveis[-1])

                        df_filtrado = df[df["Data"] == selected_day]

                        if df_filtrado.empty:
                            st.warning("Nenhum dado disponível para esta data.")
                        else:
                            df_filtrado = df_filtrado.sort_values("Horário (dia)")

                            df_filtrado["Acumulado (mm)"] = df_filtrado["Quantidade de chuva (mm)"].cumsum()

                            df_filtrado["Δt (h)"] = df_filtrado["Horário (dia)"].diff().dt.total_seconds() / 3600
                            df_filtrado["Δchuva (mm)"] = df_filtrado["Acumulado (mm)"].diff()
                            df_filtrado["Intensidade (mm/h)"] = (df_filtrado["Δchuva (mm)"] / df_filtrado["Δt (h)"]).fillna(0)

                            col1, col2, col3, col4 = st.columns(4)

                            col1.metric("Total acumulado", f"{df_filtrado['Acumulado (mm)'].iloc[-1]:.1f} mm")
                            col2.metric("Número de medições", len(df_filtrado))
                            col3.metric("Duração",
                                        f"{(df_filtrado['Horário (dia)'].iloc[-1] - df_filtrado['Horário (dia)'].iloc[0]).seconds // 60} min")
                            col4.metric("Pico de intensidade",
                                        f"{df_filtrado['Intensidade (mm/h)'].max():.1f} mm/h")

                            # ---- GRAPH 1: Accumulated Rain ----
                            fig1 = px.line(
                                df_filtrado,
                                x="Horário (dia)",
                                y="Acumulado (mm)",
                                markers=True,
                                title=f"Chuva acumulada em {selected_day}",
                                color_discrete_sequence=["#bd26a1"]
                            )
                            fig1.update_layout(xaxis_title="Horário", yaxis_title="Quantidade de chuva acumulada (mm)")
                            st.plotly_chart(fig1, use_container_width=True)

                            # ---- GRAPH 2: Intensity ----
                            fig2 = px.line(
                                df_filtrado,
                                x="Horário (dia)",
                                y="Intensidade (mm/h)",
                                markers=True,
                                title=f"Intensidade da chuva em {selected_day}",
                                color_discrete_sequence=["#bd26a1"]
                            )
                            fig2.update_layout(xaxis_title="Horário", yaxis_title="Intensidade (mm/h)")
                            st.plotly_chart(fig2, use_container_width=True)

                    else:
                        st.info("Nenhum dado de chuva disponível ainda.")

                # Sensor de nível ----------------------------------------------------------------------

                elif prefix == "n":

                    # Nível de aviso

                    st.markdown(f"""
                    <div style="
                        background-color: {cor_fundo[estado_final]};
                        padding: 15px;
                        border-radius: 10px;
                        text-align: center;
                        margin-bottom: 20px;
                        color: white;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    ">
                        <h2 style="margin:0;">NÍVEL {estado_final}: {msg_final.upper()}</h2>
                        <p style="margin:0;">Sirene: <strong>{som_final}</strong> | Rio: {nivel_real:.2f}m | Crit: {param_nivel_critico}m</p>
                    </div>
                    """, unsafe_allow_html=True)

                    df = buscar_dados_nivel(selected_id)

                    if not df.empty:
                        df["Horário (dia)"] = pd.to_datetime(df["Horário (dia)"])
                        df["Data"] = df["Horário (dia)"].dt.date

                        dias_disponiveis = sorted(df["Data"].unique())
                        selected_day = st.date_input("Selecione o dia:", dias_disponiveis[-1])

                        df_filtrado = df[df["Data"] == selected_day]

                        if df_filtrado.empty:
                            st.warning("Nenhum dado disponível para esta data.")
                        else:
                            df_filtrado = df_filtrado.sort_values("Horário (dia)")

                            # Convert cm -> meters
                            df_filtrado["Nível (m)"] = df_filtrado["Nível da água (m)"] = df_filtrado["Nível da água (m)"] = df_filtrado["Nível da água (m)"] if "Nível da água (m)" in df_filtrado else df_filtrado["waterLevelCm"] / 100

                            # KPIs -----------------------------------------------------
                            duracao_min = (df_filtrado["Horário (dia)"].iloc[-1] - df_filtrado["Horário (dia)"].iloc[0]).seconds // 60

                            col1, col2, col3, col4 = st.columns(4)
                            col1.metric("Mínimo registrado", f"{df_filtrado['Nível (m)'].min():.2f} m")
                            col2.metric("Máximo registrado", f"{df_filtrado['Nível (m)'].max():.2f} m")
                            col3.metric("Média do dia", f"{df_filtrado['Nível (m)'].mean():.2f} m")
                            col4.metric("Duração monitorada", f"{duracao_min} min")

                            # ---- LINE GRAPH ----
                            fig = px.line(
                                df_filtrado,
                                x="Horário (dia)",
                                y="Nível (m)",
                                markers=True,
                                title=f"Nível do rio em {selected_day}",
                                color_discrete_sequence=["#bd26a1"]
                            )

                            fig.update_layout(
                                xaxis_title="Horário",
                                yaxis_title="Altura da água (m)",
                            )

                            st.plotly_chart(fig, use_container_width=True)

                    else:
                        st.info("Nenhum dado de nível disponível ainda.")

                # Alerta sonoro -----------------------------------------------------------------------

                elif prefix == "b":
                    option = st.selectbox("Estado do alerta sonoro:", ["Desligado", "Ligado"])

                    # Map to numeric value
                    value = 1 if option == "Ligado" else 0

                    try:
                        response = requests.post(
                            "http://localhost:9000/sensores/alerta/beepsonoro",
                            data=str(value),
                            headers={"Content-Type": "text/plain"},
                            timeout=5
                        )
                        response.raise_for_status()
                        server_reply = response.text
                    except requests.RequestException as e:
                        st.error(f"Erro ao alterar o status do alerta sonoro: {e}")         

                    nivel_key = f"crit_level_{selected_id}"
                    nivel_critico = int(st.number_input("**Definir nível critico do rio (m):**",
                                                    min_value=0.0, step=0.1, key=nivel_key) * 100) / 100
                    if st.button("Salvar", key=f"save_b_{selected_id}"):
                        try:
                            response = requests.post(
                                "http://localhost:9000/sensores/alerta/nivelsonoro",
                                data=str(nivel_critico),
                                headers={"Content-Type": "text/plain"},
                                timeout=5
                            )
                            response.raise_for_status()
                            server_reply = response.text

                            st.success(f"Sucesso! {server_reply}")
                        except requests.RequestException as e:
                            st.error(f"Erro ao definir o nível: {e}")

                # Alerta visual -----------------------------------------------------------------
                
                elif prefix == "v":
                    st.markdown("**Alerta visual**")
                    nivel_key = f"crit_level_{selected_id}"
                    nivel_critico = int(st.number_input("**Definir nível crítico do rio (m):**",
                                                    min_value=0.0, step=0.1, key=nivel_key) * 100) / 100
                    if st.button("Salvar", key=f"save_v_{selected_id}"):
                        try:
                            response = requests.post(
                                "http://localhost:9000/sensores/alerta/nivelvisual",
                                data=str(nivel_critico),
                                headers={"Content-Type": "text/plain"},
                                timeout=5
                            )
                            response.raise_for_status()
                            server_reply = response.text

                            st.success(f"Sucesso! {server_reply}")
                        except requests.RequestException as e:
                            st.error(f"Erro ao definir o nível: {e}")

                    # Mensagens
                    newmsg_key = f"newmsg_{selected_id}"
                    send_btn_key = f"sendmsg_{selected_id}"
                    hist_key = f"hist_{selected_id}"
                    feedback_key = f"feedback_{selected_id}"

                    # Inicializa histórico e feedback se necessário
                    if hist_key not in st.session_state:
                        st.session_state[hist_key] = []
                    if feedback_key not in st.session_state:
                        st.session_state[feedback_key] = None

                    def enviar_mensagem():
                        nova_msg = st.session_state[newmsg_key].strip()
                        if not nova_msg:
                            st.session_state[feedback_key] = ("warning", "Digite uma mensagem antes de enviar.")
                            return

                        try:
                            response = requests.post(
                                "http://localhost:9000/sensores/alerta/mensagem",
                                data=nova_msg.upper().replace(" ", "||||"),
                                headers={"Content-Type": "text/plain"},
                                timeout=5
                            )
                            response.raise_for_status()
                            server_reply = response.text

                            st.session_state[hist_key].append(nova_msg)
                            st.session_state[newmsg_key] = ""  # limpa o campo de entrada

                            st.session_state[feedback_key] = ("success", server_reply)

                        except requests.RequestException as e:
                            st.session_state[feedback_key] = ("error", f"Erro ao enviar mensagem: {e}")

                    st.text_input("**Inserir mensagem a ser exibida:**", key=newmsg_key)
                    st.button("Enviar mensagem", key=send_btn_key, on_click=enviar_mensagem)

                    # Exibe o feedback logo abaixo do botão
                    feedback = st.session_state.get(feedback_key)
                    if feedback:
                        tipo, texto = feedback
                        if tipo == "success":
                            st.success(texto)
                        elif tipo == "error":
                            st.error(texto)
                        elif tipo == "warning":
                            st.warning(texto)

                    st.markdown("**Histórico de mensagens exibidas:**")
                    historico = st.session_state.get(hist_key, [])
                    if historico:
                        for msg in reversed(historico[-10:]):
                            st.markdown(f"- {msg}")
                    else:
                        st.markdown("*(Nenhuma mensagem enviada ainda)*")
        else:
            # mensagem inicial (quando nada está selecionado)
            st.markdown(
                """
                <div style="
                    background-color:#bd26a1;
                    padding: 15px;
                    border-radius: 10px;
                    color: white;
                    font-size: 16px;
                    font-weight: 500;
                ">
                    Selecione um módulo à direita para visualizar detalhes e gráficos.
                </div>
                """,
                unsafe_allow_html=True
            )

try:
    response = requests.post(
        "http://localhost:9000/sensores/alerta/beepsonoro",
        data=str(1 if som_final == "Ligado" else 0),
        headers={"Content-Type": "text/plain"},
        timeout=5
    )
    response.raise_for_status()
    server_reply = response.text
except requests.RequestException as e:
    st.error(f"Erro ao alterar o status do alerta sonoro: {e}")

try:
    response = requests.post(
        "http://localhost:9000/sensores/alerta/mensagem",
        data=str(msg_final.upper().replace(" ", "||||")),
        headers={"Content-Type": "text/plain"},
        timeout=5
    )
    response.raise_for_status()
    server_reply = response.text
except requests.RequestException as e:
    st.error(f"Erro ao definir o nível: {e}")


