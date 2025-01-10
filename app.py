from flask import Flask, request, jsonify
import json
import os

app = Flask(__name__)

# 定义保存文件路径
SAVE_FILE_PATH = "token_purchases.txt"

@app.route('/')
def home():
    return "Welcome to the Webhook Server! Monitoring wallets for token purchases."

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        # 接收交易数据
        data = request.json
        print("Received Data:", json.dumps(data, indent=4))  # 打印原始数据日志

        # 准备返回结果
        token_purchases = []

        # 解析交易数据
        for event in data:
            token_transfers = event.get("tokenTransfers", [])  # 提取代币转账信息
            for transfer in token_transfers:
                token_purchases.append({
                    "from_wallet": transfer.get("fromUserAccount"),
                    "to_wallet": transfer.get("toUserAccount"),
                    "token_mint": transfer.get("mint"),
                    "amount": transfer.get("amount"),
                })

        # 如果有代币购买记录，保存到文件
        if token_purchases:
            save_to_file(token_purchases)  # 保存为txt文件
            response = {
                "status": "success",
                "message": "Token purchases detected and saved",
                "token_purchases": token_purchases
            }
        else:
            response = {
                "status": "success",
                "message": "No token purchases detected in the transaction"
            }

        print("Processed Result:", json.dumps(response, indent=4))  # 打印处理结果日志
        return jsonify(response), 200

    except Exception as e:
        print("Error:", e)
        return jsonify({"status": "error", "message": str(e)}), 500


def save_to_file(data):
    """
    将解析的代币购买记录保存到本地 txt 文件
    """
    try:
        with open(SAVE_FILE_PATH, "a") as file:
            file.write("---- New Token Purchases ----\n")
            for entry in data:
                file.write(f"From: {entry['from_wallet']}\n")
                file.write(f"To: {entry['to_wallet']}\n")
                file.write(f"Token Mint: {entry['token_mint']}\n")
                file.write(f"Amount: {entry['amount']}\n")
                file.write("\n")
            file.write("-----------------------------\n")
        print(f"Data saved to {SAVE_FILE_PATH}")
    except Exception as e:
        print(f"Error saving to file: {e}")


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
from flask import Flask, request, jsonify
import json
import os

app = Flask(__name__)

# 保存交易数据的文件路径
TRANSACTION_LOG = "transactions.json"

# 初始化文件
if not os.path.exists(TRANSACTION_LOG):
    with open(TRANSACTION_LOG, "w") as f:
        json.dump([], f)

@app.route('/')
def home():
    return "Welcome to the Webhook Server!"

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        # 获取接收到的交易数据
        data = request.json
        print("Received Data:", data)

        # 加载现有的交易记录
        with open(TRANSACTION_LOG, "r") as f:
            transaction_log = json.load(f)

        # 处理交易数据
        for event in data:
            # 提取账户和代币变更信息
            account_data = event.get("accountData", [])
            native_transfers = event.get("nativeTransfers", [])
            token_changes = []

            for account in account_data:
                # 记录代币变更
                if account.get("tokenBalanceChanges"):
                    token_changes.append({
                        "account": account.get("account"),
                        "token_changes": account.get("tokenBalanceChanges")
                    })

            # 保存到日志
            transaction_log.append({
                "transaction": event,
                "token_changes": token_changes,
                "native_transfers": native_transfers
            })

        # 写回日志文件
        with open(TRANSACTION_LOG, "w") as f:
            json.dump(transaction_log, f, indent=4)

        return jsonify({"status": "success", "message": "Transaction recorded"}), 200
    except Exception as e:
        print("Error:", e)
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/transactions', methods=['GET'])
def get_transactions():
    try:
        # 读取并返回所有交易记录
        with open(TRANSACTION_LOG, "r") as f:
            transaction_log = json.load(f)
        return jsonify({"status": "success", "transactions": transaction_log}), 200
    except Exception as e:
        print("Error:", e)
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
