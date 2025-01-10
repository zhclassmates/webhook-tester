from flask import Flask, request, jsonify

app = Flask(__name__)

# 根路由，测试服务是否正常
@app.route('/')
def home():
    return "Welcome to the Webhook Server!"

# Webhook 接收地址
@app.route('/webhook', methods=['POST'])
def webhook():
    # 获取 POST 请求中的 JSON 数据
    data = request.json
    print("Received data:", data)  # 在日志中打印收到的数据
    # 返回响应
    return jsonify({"status": "success", "message": "Webhook received!"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
