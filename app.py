from flask import Flask, request, jsonify
import json
import time
from collections import defaultdict
import requests

app = Flask(__name__)

# Telegram 配置
TELEGRAM_BOT_TOKEN = "8147535123:AAFGpqQ3zjVYuIF4ajacST5Mxzy9oQZKDS4"  # 替换为你的 Telegram Bot Token
TELEGRAM_CHAT_ID = "-1002022664219"  # 替换为你的 Telegram Chat ID

# 存储监控的交易数据
monitor_data = defaultdict(list)

# 时间窗口
TIME_WINDOW = 120  # 2 分钟，单位秒

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
                        "amount": token_transfer.get("amount"]
                    })

        # 更新监控数据
        current_time = int(time.time())
        for purchase in token_purchases:
            monitor_data[purchase["token_mint"]].append({
                "time": current_time,
                "data": purchase
            })

        # 每 2 分钟统计并发送到 Telegram
        check_and_send_summary(current_time)

        # 返回成功响应
        return jsonify({"status": "success", "message": "Data processed"}), 200

    except Exception as e:
        # 打印错误信息到日志
        print(f"Error processing data: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

def check_and_send_summary(current_time):
    """
    每 2 分钟统计交易记录，并发送到 Telegram。
    """
    grouped_purchases = defaultdict(list)

    # 筛选 2 分钟内的交易记录
    for token, purchases in monitor_data.items():
        for purchase in purchases:
            if current_time - purchase["time"] <= TIME_WINDOW:
                grouped_purchases[token].append(purchase["data"])

    # 如果有符合条件的交易，发送到 Telegram
    if grouped_purchases:
        message = "📊 **2 分钟内交易统计**\n\n"
        for token, purchases in grouped_purchases.items():
            if len(purchases) > 1:  # 同一代币被多个钱包购买
                message += f"⚠️ **代币合约地址 {token} 被多个钱包购买:**\n"
                for purchase in purchases:
                    message += (
                        f"📍 钱包地址: {purchase['from_wallet']}\n"
                        f"➡️ 购买数量: {purchase['amount']}\n"
                        f"🔗 接收地址: {purchase['to_wallet']}\n\n"
                    )
            else:  # 单个钱包购买
                purchase = purchases[0]
                message += (
                    f"📍 钱包地址: {purchase['from_wallet']}\n"
                    f"➡️ 购买数量: {purchase['amount']}\n"
                    f"🔗 接收地址: {purchase['to_wallet']}\n\n"
                )

        send_to_telegram(message)

    # 清理过期数据
    cleanup_old_data(current_time)

def send_to_telegram(message):
    """
    将监控结果发送到 Telegram。
    """
    try:
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
    except Exception as e:
        print(f"发送到 Telegram 时出错: {str(e)}")

def cleanup_old_data(current_time):
    """
    清理超过 2 分钟的旧数据。
    """
    for token in list(monitor_data.keys()):
        monitor_data[token] = [
            purchase for purchase in monitor_data[token]
            if current_time - purchase["time"] <= TIME_WINDOW
        ]
        if not monitor_data[token]:  # 如果该代币没有数据了，则删除
            del monitor_data[token]

@app.route('/')
def home():
    return "Welcome to the Webhook Server!"

# 启动 Flask 应用
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
