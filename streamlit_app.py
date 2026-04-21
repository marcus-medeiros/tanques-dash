# -*- coding: utf-8 -*-
# DASHBOARD STREAMLIT - TANQUES VIA MQTT (SEM BANCO)

import streamlit as st
import pandas as pd
import paho.mqtt.client as mqtt
import json
import time
from datetime import datetime
import queue
import altair as alt

# --- CONFIGURAÇÕES ---
BROKER_ADDRESS = "broker.hivemq.com"
TOPIC_LEITURAS = "PROJETOS/IOT/VOLUMES/SENSOR/#"

# --- MQTT ---

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Conectado ao broker!")
        client.subscribe(TOPIC_LEITURAS)
    else:
        print("Erro na conexão:", rc)

def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode()

        try:
            dados = json.loads(payload)
            tanque = dados.get("tanque")
            nivel = dados.get("nivel")
        except:
            tanque = msg.topic.split("/")[-1]
            nivel = float(payload)

        userdata.put({
            "tanque": tanque,
            "nivel": nivel
        })

    except Exception as e:
        print("Erro:", e)

def inicializar_mqtt():
    if 'msg_queue' not in st.session_state:
        st.session_state.msg_queue = queue.Queue()

    if 'mqtt_client' not in st.session_state:
        client = mqtt.Client(userdata=st.session_state.msg_queue)
        client.on_connect = on_connect
        client.on_message = on_message

        try:
            client.connect(BROKER_ADDRESS, 1883, 60)
            client.loop_start()
            st.session_state.mqtt_client = client
        except Exception as e:
            st.error(f"Erro MQTT: {e}")

# --- STREAMLIT ---

st.set_page_config(page_title="Tanques MQTT", layout="wide")

inicializar_mqtt()

st.title("💧 Monitoramento de Tanques (Tempo Real)")

# --- ESTRUTURA EM MEMÓRIA ---
if 'dados' not in st.session_state:
    st.session_state.dados = pd.DataFrame(columns=["tanque", "nivel", "timestamp"])

# --- PROCESSA FILA MQTT ---
while not st.session_state.msg_queue.empty():
    dados = st.session_state.msg_queue.get()
    dados['timestamp'] = datetime.now()

    st.session_state.dados = pd.concat(
        [st.session_state.dados, pd.DataFrame([dados])],
        ignore_index=True
    )

# --- LIMITA TAMANHO (evita travar) ---
MAX_PONTOS = 500
if len(st.session_state.dados) > MAX_PONTOS:
    st.session_state.dados = st.session_state.dados.tail(MAX_PONTOS)

df = st.session_state.dados

# --- DASHBOARD PRINCIPAL ---

tanques = ["TANQUEA", "TANQUEB", "TANQUEC"]
col1, col2, col3 = st.columns(3)

for i, tanque in enumerate(tanques):
    df_tanque = df[df['tanque'] == tanque]

    if not df_tanque.empty:
        ultimo = df_tanque.iloc[-1]['nivel']
    else:
        ultimo = 0

    col = [col1, col2, col3][i]

    with col:
        st.subheader(tanque)
        st.metric("Nível Atual", f"{ultimo:.2f} %")

        # Alarmes simples
        if ultimo < 20:
            st.error("Nível Baixo")
        elif ultimo > 90:
            st.warning("Quase cheio")
        else:
            st.success("Normal")

# --- GRÁFICO ---

st.markdown("---")
st.subheader("📊 Histórico")

tanque_sel = st.selectbox("Selecione o tanque:", tanques)

df_sel = df[df['tanque'] == tanque_sel]

if not df_sel.empty:
    chart = alt.Chart(df_sel.tail(50)).mark_line().encode(
        x='timestamp:T',
        y=alt.Y('nivel:Q', title="Nível (%)", scale=alt.Scale(domain=[0,100])),
        tooltip=['timestamp', 'nivel']
    ).interactive()

    st.altair_chart(chart, use_container_width=True)

    # tabela
    df_display = df_sel.copy()
    df_display['timestamp'] = df_display['timestamp'].dt.strftime("%d/%m/%Y %H:%M:%S")

    st.dataframe(df_display.sort_index(ascending=False), use_container_width=True)

else:
    st.info("Sem dados ainda...")

# --- AUTO REFRESH ---
time.sleep(1)
st.rerun()
