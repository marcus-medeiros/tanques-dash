# DASHBOARD TANQUES - MQTT + GOOGLE SHEETS (VERSÃO FINAL)
from streamlit_autorefresh import st_autorefresh
import streamlit as st
import pandas as pd
import paho.mqtt.client as mqtt
import json
from datetime import datetime
import queue
import requests
import altair as alt

# --- CONFIG ---
BROKER = "broker.hivemq.com"
TOPIC = "PROJETOS/IOT/VOLUMES/SENSOR/#"

# 🔥 COLE SUA URL DO APPS SCRIPT
GOOGLE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbz38wQcW7H2ivA-Oo_achNXvThfrxAczZAa0-487Zes1exrFrnjcnZkTZX4TRL1yxaa/exec"

# --- MQTT CALLBACKS ---

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        client.subscribe(TOPIC)

def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode()

        try:
            data = json.loads(payload)
            tanque = data["tanque"]
            nivel = data["nivel"]
        except:
            tanque = msg.topic.split("/")[-1]
            nivel = float(payload)

        userdata.put((tanque, nivel, datetime.now()))

    except Exception as e:
        print("Erro:", e)

# --- INIT MQTT ---

def init_mqtt():
    if 'queue' not in st.session_state:
        st.session_state.queue = queue.Queue()

    if 'mqtt' not in st.session_state:
        client = mqtt.Client(userdata=st.session_state.queue)

        client.on_connect = on_connect
        client.on_message = on_message

        client.connect(BROKER, 1883, 60)
        client.loop_start()

        st.session_state.mqtt = client

# --- STREAMLIT CONFIG ---

st.set_page_config(layout="wide")
st.title("💧 Monitoramento de Tanques")

init_mqtt()

# --- ESTADOS ---

if 'dados' not in st.session_state:
    st.session_state.dados = []

if 'buffer_envio' not in st.session_state:
    st.session_state.buffer_envio = []

# --- FUNÇÃO ENVIO GOOGLE SHEETS ---

def enviar_para_sheets(dado):
    try:
        requests.post(GOOGLE_SCRIPT_URL, json=dado, timeout=2)
    except Exception as e:
        print("Erro envio:", e)

# --- PROCESSA MQTT ---

while not st.session_state.queue.empty():
    tanque, nivel, timestamp = st.session_state.queue.get()

    dado = {
        "tanque": tanque,
        "nivel": float(nivel),
        "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S")
    }

    st.session_state.dados.append(dado)
    st.session_state.buffer_envio.append(dado)

# --- ENVIO CONTROLADO (evita spam) ---

if len(st.session_state.buffer_envio) >= 3:
    enviar_para_sheets(st.session_state.buffer_envio[-1])
    st.session_state.buffer_envio = []

# --- DATAFRAME ---

df = pd.DataFrame(
    st.session_state.dados,
    columns=["tanque", "nivel", "timestamp"]
)

if not df.empty:
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

# --- DASHBOARD ---

tanques = ["TANQUEA", "TANQUEB", "TANQUEC"]
cols = st.columns(3)

for i, t in enumerate(tanques):
    df_t = df[df["tanque"] == t] if not df.empty else pd.DataFrame()

    valor = df_t.iloc[-1]["nivel"] if not df_t.empty else 0

    with cols[i]:
        st.subheader(t)
        st.metric("Nível", f"{valor:.1f}%")

        if valor < 20:
            st.error("⚠️ Baixo")
        elif valor > 90:
            st.warning("⚠️ Cheio")
        else:
            st.success("Normal")

# --- GRÁFICO ---

st.markdown("---")

tanque_sel = st.selectbox("Selecione o tanque", tanques)

df_sel = df[df["tanque"] == tanque_sel] if not df.empty else pd.DataFrame()

if not df_sel.empty:
    chart = alt.Chart(df_sel).mark_line().encode(
        x='timestamp:T',
        y=alt.Y('nivel:Q', scale=alt.Scale(domain=[0, 100])),
        tooltip=['timestamp', 'nivel']
    ).interactive()

    st.altair_chart(chart, use_container_width=True)

    df_display = df_sel.copy()
    df_display["timestamp"] = df_display["timestamp"].dt.strftime("%d/%m/%Y %H:%M:%S")

    st.dataframe(df_display.tail(20), use_container_width=True)

else:
    st.info("Aguardando dados MQTT...")

# --- AUTO REFRESH (SEM TRAVAR) ---
st_autorefresh(interval=2000, key="refresh")
