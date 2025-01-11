import os
import json
import sqlite3
import time
from datetime import datetime, timedelta
import requests
from collections import defaultdict
import threading
from flask import Flask

app = Flask(__name__)

# Telegram 配置
TELEGRAM_BOT_TOKEN = "8147535123:AAFGpqQ3zjVYuIF4ajacST5Mxzy9oQZKDS4"
TELEGRAM_CHAT_ID = "-1002022664219"

# Helius API 配置
API_KEY = "a8837991-562f-4a6d-91f1-a76f13f83495"
EXCHANGE_WALLETS = [
    "AaZkwhkiDStDcgrU37XAj9fpNLrD8Erz5PNkdm4k5hjy",
    "AC5RDfQFmDS1deWZos921JfqscXdByf8BKHs5ACWjtW2"
]
BASE_URL = "https://api.helius.xyz/v0/addresses/{}/transactions?api-key={}"

def init_db():
    conn = sqlite3.connect('transactions.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        from_address TEXT,
        to_address TEXT,
        amount REAL,
        timestamp DATETIME
    )''')
    conn.commit()
    conn.close()

def save_transaction(from_address, to_address, amount, timestamp):
    conn = sqlite3.connect('transactions.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO transactions (from_address, to_address, amount, timestamp)
        VALUES (?, ?, ?, ?)
    ''', (from_address, to_address, amount, timestamp))
    conn.commit()
    conn.close()

def fetch_transactions(wallet):
    try:
        url = BASE_URL.format(wallet, API_KEY)
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"获取交易记录失败: {response.text}")
            return []
    except Exception as e:
        print(f"API 请求错误: {str(e)}")
        return []

def process_exchange_transactions():
    for wallet in EXCHANGE_WALLETS:
        transactions = fetch_transactions(wallet)
        for transaction in transactions:
            native_transfers = transaction.get("nativeTransfers", [])
            timestamp = datetime.utcfromtimestamp(transaction["timestamp"])

            for transfer in native_transfers:
                from_address = transfer.get("fromUserAccount")
                to_address = transfer.get("toUserAccount")
                amount = transfer.get("amount", 0) / 10**9

                if from_address == wallet and amount < 10:
                    print(f"监测到交易: {from_address} -> {to_address}, Amount: {amount} SOL")
                    save_transaction(from_address, to_address, amount, timestamp)

def send_to_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        print("消息已发送到 Telegram")
    else:
        print(f"发送到 Telegram 失败: {response.text}")

def monitor_transactions():
    while True:
        process_exchange_transactions()
        time.sleep(10)

def send_test_message():
    while True:
        send_to_telegram("✅ 测试消息：交易监控服务正在运行...")
        time.sleep(120)

@app.route('/')
def home():
    return "Token Transaction Monitor is running!"

if __name__ == "__main__":
    init_db()
    threading.Thread(target=monitor_transactions, daemon=True).start()
    threading.Thread(target=send_test_message, daemon=True).start()

    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
