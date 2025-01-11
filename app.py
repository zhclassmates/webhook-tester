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
TELEGRAM_BOT_TOKEN = "8147535123:AAFGpqQ3zjVYuIF4ajacST5Mxzy9oQZKDS4"  # 替换为你的 Telegram Bot Token
TELEGRAM_CHAT_ID = "-1002022664219"  # 替换为你的 Telegram Chat ID

# Helius API 配置
API_KEY = "a8837991-562f-4a6d-91f1-a76f13f83495"  # 替换为你的 Helius API 密钥
EXCHANGE_WALLETS = [
    "AaZkwhkiDStDcgrU37XAj9fpNLrD8Erz5PNkdm4k5hjy",
    "AC5RDfQFmDS1deWZos921JfqscXdByf8BKHs5ACWjtW2"
]  # 替换为交易所钱包地址
BASE_URL = "https://api.helius.xyz/v0/addresses/{}/transactions?api-key={}"

# 初始化 SQLite 数据库
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

# 保存交易记录到数据库
def save_transaction(from_address, to_address, amount, timestamp):
    conn = sqlite3.connect('transactions.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO transactions (from_address, to_address, amount, timestamp)
        VALUES (?, ?, ?, ?)
    ''', (from_address, to_address, amount, timestamp))
    conn.commit()
    conn.close()

# 从 Helius API 获取交易记录
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

# 处理 API 返回的数据，筛选转出的 SOL 小于 10 的交易
def process_exchange_transactions():
    for wallet in EXCHANGE_WALLETS:
        transactions = fetch_transactions(wallet)
        for transaction in transactions:
            native_transfers = transaction.get("nativeTransfers", [])
            timestamp = datetime.utcfromtimestamp(transaction["timestamp"])

            for transfer in native_transfers:
                from_address = transfer.get("fromUserAccount")
                to_address = transfer.get("toUserAccount")
                amount = transfer.get("amount", 0) / 10**9  # 转换为 SOL 单位

                # 筛选转出的 SOL 小于 10 的交易
                if from_address == wallet and amount < 10:
                    print(f"监测到交易: {from_address} -> {to_address}, Amount: {amount} SOL")
                    save_transaction(from_address, to_address, amount, timestamp)

# 检查记录到数据库的钱包是否有后续代币购买行为
def check_token_purchases():
    conn = sqlite3.connect('transactions.db')
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT to_address FROM transactions')
    wallets = [row[0] for row in cursor.fetchall()]
    conn.close()

    # 检查这些钱包的代币购买行为
    for wallet in wallets:
        transactions = fetch_transactions(wallet)
        for transaction in transactions:
            token_transfers = transaction.get("tokenTransfers", [])
            for transfer in token_transfers:
                to_address = transfer.get("toUserAccount")
                token_mint = transfer.get("mint")
                amount = transfer.get("amount")
                timestamp = datetime.utcfromtimestamp(transaction["timestamp"])

                print(f"代币购买检测: {to_address}, Token: {token_mint}, Amount: {amount}")
                # 根据需求触发 Telegram 通知
                send_to_telegram(f"检测到钱包 {to_address} 购买代币 {token_mint}，数量: {amount}")

# 发送消息到 Telegram
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

# 定时任务：监控交易所钱包和记录到数据库的钱包
def monitor_transactions():
    while True:
        print("开始监控交易所钱包...")
        process_exchange_transactions()
        print("开始检测钱包代币购买行为...")
        check_token_purchases()
        time.sleep(10)  # 每隔 10 秒检查一次

# 定时发送测试消息到 Telegram
def send_test_message():
    while True:
        try:
            # 测试消息内容
            message = "✅ 测试消息：交易监控服务正在运行..."
            send_to_telegram(message)
        except Exception as e:
            print(f"发送测试消息失败: {str(e)}")
        # 等待两分钟
        time.sleep(120)

@app.route('/')
def home():
    return "Token Transaction Monitor is running!"

if __name__ == "__main__":
    init_db()

    # 启动监控任务
    threading.Thread(target=monitor_transactions, daemon=True).start()

    # 启动定时发送测试消息任务
    threading.Thread(target=send_test_message, daemon=True).start()

    print("监控已启动，按 Ctrl+C 停止")
    while True:
        time.sleep(1)
