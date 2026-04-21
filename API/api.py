# app.py

from flask import Flask, request, jsonify
import sqlite3
import threading
import paho.mqtt.client as mqtt
import json
from datetime import datetime

app = Flask(__name__)

# --- CONFIG ---
BROKER = "broker.hivemq.com"
TOPIC = "PROJETOS/IOT/VOLUMES/SENSOR/#"

# --- BANCO ---
def init_db():
    conn = sqlite3.connect("dados.db")
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS leituras (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tanque TEXT,
        nivel REAL,
        timestamp TEXT
    )
    """)
    conn.commit()
    conn.close()

init_db()

def salvar_dado(tanque, nivel, timestamp):
    conn = sqlite3.connect("dados.db")
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO leituras (tanque, nivel, timestamp)
        VALUES (?, ?, ?)
    """, (tanque, nivel, timestamp))

    conn.commit()
    conn.close()

# --- MQTT ---
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("MQTT conectado")
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

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        salvar_dado(tanque, nivel, timestamp)

        print(f"{tanque}: {nivel}%")

    except Exception as e:
        print("Erro MQTT:", e)

def iniciar_mqtt():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(BROKER, 1883, 60)
    client.loop_forever()

# --- ROTAS API ---
@app.route("/dados", methods=["GET"])
def listar():
    conn = sqlite3.connect("dados.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT tanque, nivel, timestamp 
        FROM leituras 
        ORDER BY id DESC 
        LIMIT 500
    """)

    rows = cursor.fetchall()
    conn.close()

    return jsonify([
        {"tanque": r[0], "nivel": r[1], "timestamp": r[2]}
        for r in rows
    ])

# --- START ---
def start_background_tasks():
    thread = threading.Thread(target=iniciar_mqtt)
    thread.daemon = True
    thread.start()

start_background_tasks()

if __name__ == "__main__":
    app.run()
