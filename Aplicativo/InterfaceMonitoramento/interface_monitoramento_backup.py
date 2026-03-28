import streamlit as st
from streamlit_autorefresh import st_autorefresh
import requests
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

def estado_de_alerta():
    i= 1

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
                    nivel_critico = int(st.number_input("**Definir nível crítico do rio (m):**",
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
