from flask import Flask, request, jsonify
import time
from collections import defaultdict
import requests

app = Flask(__name__)

# Telegram 配置
TELEGRAM_BOT_TOKEN = "8147535123:AAFGpqQ3zjVYuIF4ajacST5Mxzy9oQZKDS4"  # 替换为你的 Telegram Bot Token
TELEGRAM_CHAT_ID = "-1002022664219"      # 替换为你的 Telegram Chat ID




@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        # 获取 POST 请求的数据
        data = request.json

        # 打印接收到的原始数据到 Render 日志
        print("Received data:", json.dumps(data, indent=4))

        # 初始化代币交易记录列表
        token_transactions = []

        # 解析交易数据
        for event in data:
            for transfer in event.get("tokenTransfers", []):
                token_transactions.append({
                    "from": transfer.get("fromUserAccount"),
                    "to": transfer.get("toUserAccount"),
                    "mint": transfer.get("mint"),
                    "amount": transfer.get("amount")
                })

        # 如果有代币交易，发送到 Telegram
        if token_transactions:
            send_to_telegram(token_transactions)

        return jsonify({"status": "success", "message": "Processed successfully"}), 200

    except Exception as e:
        print(f"Error processing data: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


def send_to_telegram(token_transactions):
    """
    格式化代币交易数据并发送到 Telegram
    """
    message = "🚨 **代币交易记录**\n\n"
    for tx in token_transactions:
        message += (
            f"📍 From: {tx['from']}\n"
            f"➡️ To: {tx['to']}\n"
            f"🔗 Token Mint: {tx['mint']}\n"
            f"💰 Amount: {tx['amount']}\n\n"
        )

    # 发送到 Telegram
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


@app.route('/')
def home():
    return "Token Transaction Monitor is running!"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

