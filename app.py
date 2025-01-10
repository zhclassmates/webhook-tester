from flask import Flask, request, jsonify
import json
import time
from collections import defaultdict
import requests

app = Flask(__name__)

# Telegram 配置
TELEGRAM_BOT_TOKEN = "8147535123:AAFGpqQ3zjVYuIF4ajacST5Mxzy9oQZKDS4"  # 替换为你的 Telegram Bot Token
TELEGRAM_CHAT_ID = "-1002022664219"      # 替换为你的 Telegram Chat ID

# 存储监控的交易数据
monitor_data = defaultdict(list)

# 记录 5 分钟内的时间戳
TIME_WINDOW = 300  # 5 分钟，单位秒

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        # 接收并解析数据
        data = request.json

        # 打印接收到的原始数据到日志
        print("Received data:", json.dumps(data, indent=4))

        # 初始化解析结果
        relevant_wallets = []  # 符合条件的钱包
        token_purchases = []   # 记录购买代币的交易

        # 解析数据结构
        for event in data:
            for transfer in event.get("nativeTransfers", []):
                # 监控转移金额小于 10 SOL 的钱包
                if transfer.get("amount", 0) < 10 * (10 ** 9):  # 转换为 lamports
                    relevant_wallets.append(transfer["toUserAccount"])

            # 查找代币购买交易
            for token_transfer in event.get("tokenTransfers", []):
                if token_transfer["fromUserAccount"] in relevant_wallets:
                    token_purchases.append({
                        "from_wallet": token_transfer.get("fromUserAccount"),
                        "to_wallet": token_transfer.get("toUserAccount"),
                        "token_mint": token_transfer.get("mint"),
                        "amount": token_transfer.get("amount")
                    })

        # 更新监控数据
        current_time = int(time.time())
        for purchase in token_purchases:
            monitor_data[purchase["from_wallet"]].append({
                "time": current_time,
                "data": purchase
            })

        # 发送结果到 Telegram
        send_to_telegram(relevant_wallets, token_purchases)

        # 清理超过 5 分钟的旧数据
        cleanup_old_data(current_time)

        # 返回成功响应
        return jsonify({"status": "success", "message": "Data processed"}), 200

    except Exception as e:
        # 打印错误信息到日志
        print(f"Error processing data: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

def send_to_telegram(relevant_wallets, token_purchases):
    """
    将监控结果发送到 Telegram。
    """
    if not relevant_wallets and not token_purchases:
        return  # 如果没有符合条件的数据，则不发送

    # 构建消息
    message = "🚨 **监控结果**\n\n"
    if relevant_wallets:
        message += "📌 转移金额小于 10 SOL 的钱包地址:\n"
        for wallet in relevant_wallets:
            message += f"- {wallet}\n"

    if token_purchases:
        message += "\n📌 **购买的代币信息**:\n"
        for purchase in token_purchases:
            message += (
                f"📍 地址: {purchase['from_wallet']}\n"
                f"➡️ 购买代币: {purchase['amount']}\n"
                f"🔗 合约地址: {purchase['token_mint']}\n\n"
            )

    # 检查 5 分钟内的活跃交易
    multiple_purchases = check_multiple_purchases()
    if multiple_purchases:
        message += "⚠️ **5 分钟内同时购买的代币:**\n"
        for wallet, purchases in multiple_purchases.items():
            message += f"👜 钱包: {wallet}\n"
            for purchase in purchases:
                message += (
                    f"  ➡️ 代币: {purchase['data']['token_mint']}, "
                    f"数量: {purchase['data']['amount']}\n"
                )
            message += "\n"

    # 发送到 Telegram
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

def check_multiple_purchases():
    """
    检查 5 分钟内的多次购买行为。
    """
    current_time = int(time.time())
    result = {}
    for wallet, purchases in monitor_data.items():
        # 筛选 5 分钟内的交易
        recent_purchases = [
            purchase for purchase in purchases
            if current_time - purchase["time"] <= TIME_WINDOW
        ]
        if len(recent_purchases) > 1:  # 如果有多次购买行为
            result[wallet] = recent_purchases
    return result

def cleanup_old_data(current_time):
    """
    清理超过 5 分钟的旧数据。
    """
    for wallet in list(monitor_data.keys()):
        monitor_data[wallet] = [
            purchase for purchase in monitor_data[wallet]
            if current_time - purchase["time"] <= TIME_WINDOW
        ]
        if not monitor_data[wallet]:  # 如果该钱包没有数据了，则删除
            del monitor_data[wallet]

@app.route('/')
def home():
    return "Welcome to the Webhook Server!"

# 启动 Flask 应用
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
