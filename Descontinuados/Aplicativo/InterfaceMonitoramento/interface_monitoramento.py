import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import os

base_logo_path = os.path.dirname(os.path.abspath(__file__))
logo_path = os.path.join(base_logo_path, "imgs", "logo.png")

# --- Configuração da página ---
st.set_page_config(layout="wide", page_title="Monitoramento de Rios")

# --- CSS e título ---
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

# --- Buscar módulos do servidor ---
url = "http://localhost:9000/sensores/listar/todos"
try:
    response = requests.get(url, timeout=5)
    response.raise_for_status()
    modules = response.json()
except requests.RequestException as e:
    st.error(f"Erro ao buscar dados do servidor: {e}")
    modules = []

# --- Mapeamentos ---
type_names = {"a": "Som", "m": "LED", "b": "Pluv", "u": "Nível"}
prefix_titles = {"b": "Alerta Sonoro", "n": "Sensor de Nível", "p": "Pluviômetro", "v": "Alerta Visual"}

# Caminho absoluto para a pasta imgs
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(BASE_DIR, "imgs")
image_paths = {
    "b": os.path.join(IMG_DIR, "speaker-w.png"),
    "n": os.path.join(IMG_DIR, "ultrassonic-sensor-w.png"),
    "p": os.path.join(IMG_DIR, "rain-gauge2-w.png"),
    "v": os.path.join(IMG_DIR, "led2-w.png")
}

# inicializa session_state se necessário
if "selected_filter" not in st.session_state:
    st.session_state.selected_filter = "todos"
if "selected_module" not in st.session_state:
    st.session_state.selected_module = None

# --- Interface principal ---
if not modules:
    st.warning("Nenhum módulo encontrado no servidor.")
else:
    col1, col2 = st.columns([2, 1], gap="large")

    # --- Coluna direita: lista e filtros ---
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
                        # não precisa st.rerun — o Streamlit vai rerun automaticamente e left atualizará

    # --- Coluna esquerda: painel de detalhes (somente atualiza quando selected_module muda) ---
    with col1:
        selected_id = st.session_state.get("selected_module", None)
        if selected_id:
            # procura o módulo no conjunto completo (não no filtered_modules)
            selected_module = next((m for m in modules if m["deviceId"] == selected_id), None)
            if selected_module:
                prefix = selected_module["deviceId"][0].lower()
                dtype = selected_module["deviceType"].lower()
                device_name = type_names.get(dtype, dtype.upper())
                device_number = selected_module["deviceId"][-2:]

                # Cabeçalho (isso é estático e não perde estado)
                st.subheader(f"Detalhes do {device_name} {device_number}")
                st.markdown(f"**Descrição:** {selected_module['description']}")
                st.markdown(f"**Tipo:** {device_name.capitalize()}")
                st.markdown("**Status:** 🟢 Ativo")
                st.markdown("<hr style='margin-top:5px;'>", unsafe_allow_html=True)

                # --- Conteúdo específico por prefix (USO DE KEYS ESTÁVEIS) ---
                if prefix == "p":  # pluviômetro
                    chuva_data = pd.DataFrame({
                        "Tempo (h)": list(range(0, 10)),
                        "Quantidade de Chuva (mm)": [0, 0.5, 2.3, 3.1, 0.8, 4.2, 1.7, 0.9, 0.0, 0.3],
                    })
                    intensidade_data = pd.DataFrame({
                        "Tempo (h)": list(range(0, 10)),
                        "Intensidade (mm/h)": [0, 1.2, 4.5, 6.1, 2.5, 7.3, 3.0, 1.8, 0.5, 0.7],
                    })

                    fig1 = px.line(chuva_data, x="Tempo (h)", y="Quantidade de Chuva (mm)",
                                   markers=True, title="Quantidade de chuva por tempo",
                                   color_discrete_sequence=["#bd26a1"])
                    st.plotly_chart(fig1, use_container_width=True)

                    fig2 = px.line(intensidade_data, x="Tempo (h)", y="Intensidade (mm/h)",
                                   markers=True, title="Intensidade de chuva por tempo",
                                   color_discrete_sequence=["#bd26a1"])
                    st.plotly_chart(fig2, use_container_width=True)
                    st.caption("Dados simulados apenas para demonstração.")

                elif prefix == "n":  # sensor de nível
                    nivel_data = pd.DataFrame({
                        "Tempo (h)": list(range(0, 10)),
                        "Nível do Rio (m)": [0.8, 1.1, 1.5, 1.7, 1.2, 1.8, 1.4, 1.9, 2.0, 1.6],
                    })
                    fig = px.line(nivel_data, x="Tempo (h)", y="Nível do Rio (m)",
                                  markers=True, title="Variação do nível do rio",
                                  color_discrete_sequence=["#bd26a1"])
                    st.plotly_chart(fig, use_container_width=True)
                    st.caption("Dados simulados apenas para demonstração.")

                elif prefix == "b":  # alerta sonoro
                    st.markdown("**Estado do alerta sonoro**")
                    st.markdown("**Atualmente:** Desativado")
                    # key estável por módulo
                    nivel_key = f"crit_level_{selected_id}"
                    nivel_critico = st.number_input("**Definir nível crítico do rio (m):**",
                                                    min_value=0.0, step=0.1, key=nivel_key)
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
                            st.error(f"Erro ao enviar mensagem: {e}")

                elif prefix == "v":  # alerta visual
                    st.markdown("**Alerta visual**")
                    nivel_key = f"crit_level_{selected_id}"
                    nivel_critico = st.number_input("**Definir nível crítico do rio (m):**",
                                                    min_value=0.0, step=0.1, key=nivel_key)
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
                            st.error(f"Erro ao enviar mensagem: {e}")

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
                                data=nova_msg,
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
