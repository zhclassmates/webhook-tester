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
