from flask import Flask, jsonify
app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({"message": "Hello from AI-Powered DevOps Pipeline!"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)