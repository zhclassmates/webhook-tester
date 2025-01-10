from flask import Flask, request, jsonify
import time
from collections import defaultdict
import requests

app = Flask(__name__)

# Telegram 配置
TELEGRAM_BOT_TOKEN = "8147535123:AAFGpqQ3zjVYuIF4ajacST5Mxzy9oQZKDS4"  # 替换为你的 Telegram Bot Token
TELEGRAM_CHAT_ID = "-1002022664219"      # 替换为你的 Telegram Chat ID


# 数据存储
monitor_data = defaultdict(list)
TIME_WINDOW = 120  # 2 分钟

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        # 接收并解析请求数据
        data = request.json
        print("Received data:", data)

        relevant_wallets = []  # 转账金额小于 10 SOL 的钱包
        token_purchases = []   # 代币购买记录

        # 解析事件数据
        for event in data:
            # 解析 nativeTransfers 数据
            for transfer in event.get("nativeTransfers", []):
                amount = transfer.get("amount", None)
                if amount is not None and amount < 10 * (10 ** 9):  # 小于 10 SOL
                    relevant_wallets.append(transfer.get("toUserAccount", "Unknown"))

            # 解析 tokenTransfers 数据
            for token_transfer in event.get("tokenTransfers", []):
                from_account = token_transfer.get("fromUserAccount", None)
                if from_account in relevant_wallets:
                    token_purchases.append({
                        "from_wallet": from_account,
                        "to_wallet": token_transfer.get("toUserAccount", "Unknown"),
                        "token_mint": token_transfer.get("mint", "Unknown"),
                        "amount": token_transfer.get("amount", 0)
                    })

        # 保存监控数据
        current_time = int(time.time())
        for purchase in token_purchases:
            monitor_data[purchase["token_mint"]].append({
                "time": current_time,
                "data": purchase
            })

        # 每两分钟统计并发送到 Telegram
        send_to_telegram(relevant_wallets, token_purchases)

        # 清理过期数据
        cleanup_old_data(current_time)

        return jsonify({"status": "success", "message": "Data processed"}), 200
    except Exception as e:
        print(f"Error processing data: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

def send_to_telegram(relevant_wallets, token_purchases):
    """
    将监控结果发送到 Telegram。
    """
    current_time = int(time.time())

    # 构建消息
    if not relevant_wallets and not token_purchases:
        # 如果没有符合条件的交易，发送测试消息
        send_message_to_telegram("测试消息：过去两分钟内没有符合条件的交易。")
        return

    message = "🚨 **交易监控结果**\n\n"

    # 小于 10 SOL 的钱包
    if relevant_wallets:
        message += "📌 转账金额小于 10 SOL 的钱包地址:\n"
        for wallet in relevant_wallets:
            message += f"- {wallet}\n"

    # 代币购买记录
    if token_purchases:
        message += "\n📌 **代币购买记录**:\n"
        for purchase in token_purchases:
            message += (
                f"📍 地址: {purchase['from_wallet']}\n"
                f"➡️ 购买代币: {purchase['amount']}\n"
                f"🔗 合约地址: {purchase['token_mint']}\n\n"
            )

    # 检查 2 分钟内的代币分组情况
    grouped_purchases = group_token_purchases(current_time)
    if grouped_purchases:
        message += "⚠️ **两分钟内被多个钱包购买的代币:**\n"
        for token_mint, purchases in grouped_purchases.items():
            message += f"🔗 合约地址: {token_mint}\n"
            for purchase in purchases:
                message += (
                    f"  ➡️ 钱包: {purchase['data']['from_wallet']}, "
                    f"数量: {purchase['data']['amount']}\n"
                )
            message += "\n"

    # 发送消息到 Telegram
    send_message_to_telegram(message)

def send_message_to_telegram(message):
    """
    将消息发送到 Telegram。
    """
    telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    response = requests.post(telegram_url, json=payload)

    if response.status_code == 200:
        print("消息已发送到 Telegram")
    else:
        print(f"发送到 Telegram 失败: {response.text}")

def group_token_purchases(current_time):
    """
    分组统计两分钟内被多个钱包购买的代币。
    """
    grouped = {}
    for token_mint, purchases in monitor_data.items():
        recent_purchases = [
            purchase for purchase in purchases
            if current_time - purchase["time"] <= TIME_WINDOW
        ]
        if len(recent_purchases) > 1:
            grouped[token_mint] = recent_purchases
    return grouped

def cleanup_old_data(current_time):
    """
    清理过期的监控数据。
    """
    for token_mint in list(monitor_data.keys()):
        monitor_data[token_mint] = [
            purchase for purchase in monitor_data[token_mint]
            if current_time - purchase["time"] <= TIME_WINDOW
        ]
        if not monitor_data[token_mint]:
            del monitor_data[token_mint]

@app.route('/')
def home():
    return "Welcome to the Webhook Server!"

# 启动 Flask 应用
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
