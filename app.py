from flask import Flask, request, jsonify
import json
import time
from collections import defaultdict
import requests
from threading import Timer

# 初始化 Flask 应用
app = Flask(__name__)

# Telegram 配置
TELEGRAM_BOT_TOKEN = "8147535123:AAFGpqQ3zjVYuIF4ajacST5Mxzy9oQZKDS4"  # 替换为你的 Telegram Bot Token
TELEGRAM_CHAT_ID = "-1002022664219"      # 替换为你的 Telegram Chat ID

# 存储监控的交易数据
monitor_data = defaultdict(list)  # 用于存储 2 分钟内的交易数据
TIME_WINDOW = 120  # 时间窗口（2 分钟）

@app.route('/')
def home():
    """
    默认首页路由
    """
    return "Welcome to the Webhook Server!"

@app.route('/webhook', methods=['POST'])
def webhook():
    """
    Webhook 接收交易数据
    """
    try:
        # 接收 JSON 数据
        data = request.json

        # 打印日志以验证接收数据
        print("Received data:", json.dumps(data, indent=4))

        # 筛选转账金额小于 10 SOL 的交易
        relevant_wallets = []  # 符合条件的钱包
        token_purchases = []   # 符合条件的代币购买信息

        # 遍历接收到的事件
        for event in data:
            # 筛选 nativeTransfers（转账记录）
            for transfer in event.get("nativeTransfers", []):
                # 转账金额小于 10 SOL
                if transfer.get("amount", 0) < 10 * (10 ** 9):  # 转换为 lamports
                    relevant_wallets.append(transfer["toUserAccount"])

            # 查找 tokenTransfers（代币购买）
            for token_transfer in event.get("tokenTransfers", []):
                if token_transfer["fromUserAccount"] in relevant_wallets:
                    token_purchases.append({
                        "from_wallet": token_transfer.get("fromUserAccount"),
                        "to_wallet": token_transfer.get("toUserAccount"),
                        "token_mint": token_transfer.get("mint"),
                        "amount": token_transfer.get("amount")
                    })

        # 记录符合条件的交易
        current_time = int(time.time())
        for purchase in token_purchases:
            monitor_data[purchase["from_wallet"]].append({
                "time": current_time,
                "data": purchase
            })

        # 返回成功响应
        return jsonify({"status": "success", "message": "Data processed"}), 200

    except Exception as e:
        print(f"Error processing data: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

def send_to_telegram():
    """
    定期统计符合条件的交易并发送到 Telegram
    """
    try:
        current_time = int(time.time())
        grouped_purchases = defaultdict(list)  # 分组存储同一代币的购买情况
        token_purchases = []

        # 筛选时间窗口内的交易
        for wallet, purchases in monitor_data.items():
            recent_purchases = [
                purchase for purchase in purchases
                if current_time - purchase["time"] <= TIME_WINDOW
            ]
            for purchase in recent_purchases:
                token_purchases.append(purchase["data"])
                grouped_purchases[purchase["data"]["token_mint"]].append(purchase["data"])

        # 如果没有符合条件的交易，不发送消息
        if not token_purchases:
            return

        # 构建 Telegram 消息
        message = "📊 **2分钟代币购买统计（小于 10 SOL）**\n\n"

        # 普通交易统计
        message += "✅ **代币购买情况**:\n"
        for purchase in token_purchases:
            message += (
                f"  - 钱包地址: {purchase['from_wallet']}\n"
                f"    代币地址: {purchase['token_mint']}\n"
                f"    代币数量: {purchase['amount']}\n\n"
            )

        # 重点标注：同一代币被多个钱包购买
        message += "🚨 **重点交易 (多个钱包购买同一代币)**:\n"
        for token_address, purchases in grouped_purchases.items():
            if len(purchases) > 1:  # 如果同一代币被多个钱包购买
                message += f"  - 代币地址: {token_address}\n"
                for purchase in purchases:
                    message += (
                        f"    - 钱包地址: {purchase['from_wallet']}\n"
                        f"      数量: {purchase['amount']}\n"
                    )
                message += "\n"

        # 发送消息到 Telegram
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
        print(f"Error sending to Telegram: {str(e)}")

    # 清理超过时间窗口的旧数据
    cleanup_old_data(current_time)

    # 设置下一次发送任务
    Timer(TIME_WINDOW, send_to_telegram).start()

def cleanup_old_data(current_time):
    """
    清理超过时间窗口的旧数据
    """
    for wallet in list(monitor_data.keys()):
        monitor_data[wallet] = [
            purchase for purchase in monitor_data[wallet]
            if current_time - purchase["time"] <= TIME_WINDOW
        ]
        if not monitor_data[wallet]:  # 如果该钱包没有数据了，则删除
            del monitor_data[wallet]

# 启动 Flask 应用
if __name__ == '__main__':
    # 启动定时统计任务
    Timer(TIME_WINDOW, send_to_telegram).start()

    # 启动 Flask 服务
    app.run(host='0.0.0.0', port=5000)
