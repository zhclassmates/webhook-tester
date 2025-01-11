import json
import time
import sqlite3
from flask import Flask, request, jsonify
import requests
from datetime import datetime, timedelta
from collections import defaultdict
import threading

app = Flask(__name__)

# Telegram 配置
TELEGRAM_BOT_TOKEN = "8147535123:AAFGpqQ3zjVYuIF4ajacST5Mxzy9oQZKDS4"  # 替换为你的 Telegram Bot Token
TELEGRAM_CHAT_ID = "-1002022664219"      # 替换为你的 Telegram Chat ID

# 初始化 SQLite 数据库
def init_db():
    conn = sqlite3.connect('transactions.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        from_address TEXT,
        to_address TEXT,
        token_mint TEXT,
        amount INTEGER,
        timestamp DATETIME
    )''')
    conn.commit()
    conn.close()

# 保存代币交易到数据库
def save_transaction(from_address, to_address, token_mint, amount):
    conn = sqlite3.connect('transactions.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO transactions (from_address, to_address, token_mint, amount, timestamp)
        VALUES (?, ?, ?, ?, ?)
    ''', (from_address, to_address, token_mint, amount, datetime.now()))
    conn.commit()
    conn.close()

# 查找 15 分钟内的共同购买
def find_common_purchases(from_address):
    conn = sqlite3.connect('transactions.db')
    cursor = conn.cursor()

    # 获取该地址的最后一笔交易
    cursor.execute('''
        SELECT token_mint, timestamp FROM transactions
        WHERE from_address = ? ORDER BY timestamp DESC LIMIT 1
    ''', (from_address,))
    last_transaction = cursor.fetchone()

    if last_transaction:
        token_mint, last_timestamp = last_transaction
        last_time = datetime.strptime(last_timestamp, '%Y-%m-%d %H:%M:%S')
        time_window = last_time - timedelta(minutes=15)

        # 查找过去 15 分钟内购买相同代币的交易
        cursor.execute('''
            SELECT from_address, token_mint FROM transactions
            WHERE token_mint = ? AND timestamp >= ?
        ''', (token_mint, time_window))
        common_transactions = cursor.fetchall()
        
        # 格式化共同交易数据
        common_wallets = defaultdict(list)
        for tx in common_transactions:
            common_wallets[tx[0]].append(tx[1])
        
        return common_wallets

    conn.close()
    return {}

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

# Webhook 接收代币交易数据
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        # 获取传入的数据
        data = request.json
        print("Received data:", json.dumps(data, indent=4))

        # 初始化代币交易记录列表
        token_transactions = []

        for event in data:
            for transfer in event.get("tokenTransfers", []):
                from_address = transfer.get("fromUserAccount")
                to_address = transfer.get("toUserAccount")
                token_mint = transfer.get("mint")
                amount = transfer.get("amount")

                # 保存交易到数据库
                save_transaction(from_address, to_address, token_mint, amount)

                token_transactions.append({
                    "from": from_address,
                    "to": to_address,
                    "mint": token_mint,
                    "amount": amount
                })

                # 如果交易时间小于 10 秒，开始监控
                if amount and time_diff_less_than_10_seconds(from_address):
                    common_purchases = find_common_purchases(from_address)
                    if common_purchases:
                        send_to_telegram(format_common_purchases(common_purchases))

        # 返回成功消息
        return jsonify({"status": "success", "message": "Processed successfully"}), 200

    except Exception as e:
        print(f"Error processing data: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

def time_diff_less_than_10_seconds(from_address):
    """检查最后一笔交易与现在的时间差是否小于 10 秒"""
    conn = sqlite3.connect('transactions.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT timestamp FROM transactions
        WHERE from_address = ? ORDER BY timestamp DESC LIMIT 1
    ''', (from_address,))
    last_transaction = cursor.fetchone()

    if last_transaction:
        last_time = datetime.strptime(last_transaction[0], '%Y-%m-%d %H:%M:%S')
        if (datetime.now() - last_time).total_seconds() < 10:
            return True
    conn.close()
    return False

def format_common_purchases(common_purchases):
    """格式化共同购买的代币信息"""
    message = "🚨 **共同购买的代币记录**\n\n"
    for wallet, tokens in common_purchases.items():
        message += f"📍 Wallet: {wallet}\n"
        for token in tokens:
            message += f"🔗 Token Mint: {token}\n"
        message += "\n"
    return message

# 每 2 分钟发送一次测试消息
def send_test_message():
    while True:
        time.sleep(120)
        send_to_telegram("✅ 测试：Token Transaction Monitor 正在运行！")

@app.route('/')
def home():
    return "Token Transaction Monitor is running!"

if __name__ == '__main__':
    init_db()

    # 启动测试消息的线程
    threading.Thread(target=send_test_message, daemon=True).start()

    app.run(host='0.0.0.0', port=5000)
