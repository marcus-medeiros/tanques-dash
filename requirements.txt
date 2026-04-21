# -*- coding: utf-8 -*-
# DASHBOARD TANQUES - MQTT + SQLITE (VERSÃO ESTÁVEL)

import streamlit as st
import pandas as pd
import paho.mqtt.client as mqtt
import json
import time
from datetime import datetime
import queue
import sqlite3
import altair as alt
import os

# --- CONFIG ---
BROKER = "broker.hivemq.com"
PORT = 1883
TOPIC = "PROJETOS/IOT/VOLUMES/SENSOR/#"

DB = os.path.join(os.getcwd(), "tanques.db")

# --- BANCO DE DADOS ---

def init_db():
    conn = sqlite3.connect(DB, check_same_thread=False)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS leituras (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tanque TEXT,
        nivel REAL,
        timestamp DATETIME
    )
    """)

    conn.commit()
    return conn

def insert_lote(conn, dados_lote):
    cursor = conn.cursor()

    cursor.executemany("""
        INSERT INTO leituras (tanque, nivel, timestamp)
        VALUES (?, ?, ?)
    """, dados_lote)

    conn.commit()

def load_data():
    conn = sqlite3.connect(DB)
    df = pd.read_sql_query(
        "SELECT * FROM leituras ORDER BY timestamp DESC LIMIT 500",
        conn
    )
    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    return df

# --- MQTT (API ANTIGA - COMPATÍVEL) ---

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("MQTT conectado")
        client.subscribe(TOPIC)
    else:
        print("Erro MQTT:", rc)

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

def init_mqtt():
    if 'queue' not in st.session_state:
        st.session_state.queue = queue.Queue()

    if 'mqtt' not in st.session_state:
        client = mqtt.Client(userdata=st.session_state.queue)

        client.on_connect = on_connect
        client.on_message = on_message

        client.connect(BROKER, PORT, 60)
        client.loop_start()

        st.session_state.mqtt = client

# --- STREAMLIT ---

st.set_page_config(layout="wide")
st.title("💧 Monitoramento de Tanques (MQTT + SQLite)")

st.caption(f"Banco em: {DB}")

conn = init_db()
init_mqtt()

# --- BUFFER ---
if 'buffer' not in st.session_state:
    st.session_state.buffer = []

# --- PROCESSA FILA MQTT ---
while not st.session_state.queue.empty():
    st.session_state.buffer.append(st.session_state.queue.get())

# --- INSERT EM LOTE ---
if len(st.session_state.buffer) >= 10:
    insert_lote(conn, st.session_state.buffer)
    st.session_state.buffer = []

# --- CARREGA DADOS ---
df = load_data()

tanques = ["TANQUEA", "TANQUEB", "TANQUEC"]
cols = st.columns(3)

for i, t in enumerate(tanques):
    df_t = df[df['tanque'] == t]

    valor = df_t.iloc[0]['nivel'] if not df_t.empty else 0

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

df_sel = df[df['tanque'] == tanque_sel].sort_values("timestamp")

if not df_sel.empty:
    chart = alt.Chart(df_sel).mark_line().encode(
        x='timestamp:T',
        y=alt.Y('nivel:Q', title="Nível (%)", scale=alt.Scale(domain=[0, 100])),
        tooltip=['timestamp', 'nivel']
    ).interactive()

    st.altair_chart(chart, use_container_width=True)

    # tabela formatada
    df_display = df_sel.copy()
    df_display['timestamp'] = pd.to_datetime(df_display['timestamp'], errors='coerce')
    df_display['timestamp'] = df_display['timestamp'].dt.strftime("%d/%m/%Y %H:%M:%S")

    st.dataframe(df_display.tail(20), use_container_width=True)

else:
    st.info("Sem dados ainda...")

# --- AUTO REFRESH ---
time.sleep(2)
st.rerun()
