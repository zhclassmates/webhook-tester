from flask import Flask, request, jsonify
import json

app = Flask(__name__)

# Webhook 接收处理函数
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        # 接收并解析数据
        data = request.json

        # 打印接收到的原始数据到日志
        print("Received data:", json.dumps(data, indent=4))

        # 初始化解析结果
        token_purchases = []

        # 解析数据结构
        for event in data:
            for transfer in event.get("tokenTransfers", []):
                token_purchases.append({
                    "from_wallet": transfer.get("fromUserAccount"),
                    "to_wallet": transfer.get("toUserAccount"),
                    "token_mint": transfer.get("mint"),
                    "amount": transfer.get("amount")
                })

        # 打印解析后的结果到日志
        print("Processed data: Token purchases detected:")
        for purchase in token_purchases:
            print(f"From wallet: {purchase['from_wallet']}")
            print(f"To wallet: {purchase['to_wallet']}")
            print(f"Token Mint: {purchase['token_mint']}")
            print(f"Amount: {purchase['amount']}")

        # 保存解析结果到文件
        with open("token_purchases.txt", "w") as file:
            file.write("Processed token purchases:\n")
            for purchase in token_purchases:
                file.write(f"From wallet: {purchase['from_wallet']}\n")
                file.write(f"To wallet: {purchase['to_wallet']}\n")
                file.write(f"Token Mint: {purchase['token_mint']}\n")
                file.write(f"Amount: {purchase['amount']}\n")
                file.write("\n")

        # 返回成功响应
        return jsonify({"status": "success", "message": "Data processed"}), 200

    except Exception as e:
        # 打印错误信息到日志
        print(f"Error processing data: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

# 默认首页路由
@app.route('/')
def home():
    return "Welcome to the Webhook Server!"

# 启动 Flask 应用
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
