from flask import Flask, request, jsonify
import time
from collections import defaultdict
import requests

app = Flask(__name__)

# Telegram 配置
TELEGRAM_BOT_TOKEN = "8147535123:AAFGpqQ3zjVYuIF4ajacST5Mxzy9oQZKDS4"  # 替换为你的 Telegram Bot Token
TELEGRAM_CHAT_ID = "-1002022664219"      # 替换为你的 Telegram Chat ID

# 存储监控的数据
transactions_data = []
address_tracker = defaultdict(list)
SCAN_INTERVAL = 120  # 2 分钟
MIN_AMOUNT = 10 * (10 ** 9)  # 转换为 lamports 表示 10 SOL

# 处理 Webhook 请求
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.json

        # 打印接收的原始数据
        print("Received data:", data)

        current_time = int(time.time())
        low_balance_wallets = []  # 记录小于 10 SOL 的钱包
        token_purchases = []  # 记录代币购买的情况

        # 遍历 nativeTransfers 检查转账金额
        for event in data:
            for transfer in event.get("nativeTransfers", []):
                amount = transfer.get("amount", 0)
                if amount > 0 and amount < MIN_AMOUNT:  # 小于 10 SOL 的转账
                    low_balance_wallets.append(transfer["toUserAccount"])
                    # 保存该钱包和时间
                    address_tracker[transfer["toUserAccount"]].append(current_time)

            # 检查 tokenTransfers 记录代币购买
            for token_transfer in event.get("tokenTransfers", []):
                token_purchases.append({
                    "from_wallet": token_transfer["fromUserAccount"],
                    "to_wallet": token_transfer["toUserAccount"],
                    "token_mint": token_transfer["mint"],
                    "amount": token_transfer["amount"],
                })

        # 将监控结果保存
        transactions_data.append({"time": current_time, "wallets": low_balance_wallets, "tokens": token_purchases})

        # 定时发送 Telegram 消息
        if current_time % SCAN_INTERVAL == 0:  # 每 2 分钟执行
            send_summary_to_telegram()

        return jsonify({"status": "success", "message": "Data processed"}), 200

    except Exception as e:
        print(f"Error processing data: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


def send_summary_to_telegram():
    """
    构建并发送交易摘要到 Telegram。
    """
    global transactions_data
    current_time = int(time.time())
    recent_transactions = [tx for tx in transactions_data if current_time - tx["time"] <= SCAN_INTERVAL]
    
    message = "🚨 **监控结果**\n\n"

    # 收集小于 10 SOL 的钱包
    wallets = set()
    for tx in recent_transactions:
        for wallet in tx["wallets"]:
            wallets.add(wallet)
    
    if wallets:
        message += "📌 转账金额小于 10 SOL 的钱包地址:\n"
        for wallet in wallets:
            message += f"- {wallet}\n"

    # 分组统计代币购买
    token_groups = defaultdict(list)
    for tx in recent_transactions:
        for token in tx["tokens"]:
            token_groups[token["token_mint"]].append(token)

    if token_groups:
        message += "\n📌 **代币购买情况**:\n"
        for token_mint, purchases in token_groups.items():
            if len(purchases) > 1:  # 如果同一代币被多个钱包购买
                message += f"⚠️ 代币: {token_mint}\n"
                for purchase in purchases:
                    message += (
                        f"  - 钱包: {purchase['from_wallet']}, "
                        f"购买数量: {purchase['amount']}\n"
                    )
            else:
                for purchase in purchases:
                    message += (
                        f"📍 代币: {token_mint}, "
                        f"钱包: {purchase['from_wallet']}, "
                        f"购买数量: {purchase['amount']}\n"
                    )

    # 如果没有符合条件的交易，发送测试语句
    if not wallets and not token_groups:
        message = "📝 **测试结果**: 暂无符合条件的交易。"

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
        print(f"发送消息到 Telegram 失败: {response.text}")

    # 清理已处理的交易
    transactions_data = [tx for tx in transactions_data if current_time - tx["time"] <= SCAN_INTERVAL]


@app.route('/')
def home():
    return "Welcome to the Webhook Server!"


# 启动 Flask 应用
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
