# DASHBOARD TANQUES - MQTT + API (VERSÃO ESTÁVEL)

import streamlit as st
import pandas as pd
import paho.mqtt.client as mqtt
import json
from datetime import datetime
import queue
import requests
import altair as alt
from streamlit_autorefresh import st_autorefresh

# --- CONFIG ---
BROKER = "broker.hivemq.com"
TOPIC = "PROJETOS/IOT/VOLUMES/SENSOR/#"

# 🔥 SUA API NO RENDER
API_URL = "https://seu-app.onrender.com/dados"

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
        print("Erro MQTT:", e)

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

# --- ENVIO PARA API ---

def enviar_para_api(dado):
    try:
        requests.post(API_URL, json=dado, timeout=1)
    except:
        pass  # evita travar

# --- LEITURA DA API ---

def carregar_dados():
    try:
        r = requests.get(API_URL, timeout=2)
        data = r.json()

        df = pd.DataFrame(data)

        if not df.empty:
            df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

        return df

    except Exception as e:
        st.warning(f"Erro ao carregar dados: {e}")
        return pd.DataFrame()

# --- STREAMLIT ---

st.set_page_config(layout="wide")
st.title("💧 Monitoramento de Tanques (API)")

init_mqtt()

# --- PROCESSA MQTT ---

while not st.session_state.queue.empty():
    tanque, nivel, timestamp = st.session_state.queue.get()

    dado = {
        "tanque": tanque,
        "nivel": float(nivel),
        "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S")
    }

    enviar_para_api(dado)

# --- CARREGA DADOS DA API ---

df = carregar_dados()

# --- DASHBOARD ---

tanques = ["TANQUEA", "TANQUEB", "TANQUEC"]
cols = st.columns(3)

for i, t in enumerate(tanques):
    df_t = df[df["tanque"] == t] if not df.empty else pd.DataFrame()

    valor = df_t.iloc[0]["nivel"] if not df_t.empty else 0

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
    df_sel = df_sel.sort_values("timestamp")

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
    st.info("Aguardando dados...")

# --- AUTO REFRESH ---
st_autorefresh(interval=2000, key="refresh")
