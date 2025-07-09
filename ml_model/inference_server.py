from flask import Flask, request, jsonify
import joblib
import os

app = Flask(__name__)
model = joblib.load("model.pkl")

@app.route('/ping', methods=['GET'])
def ping():
    return "OK", 200

@app.route('/invocations', methods=['POST'])
def invoke():
    data = request.get_json()
    prediction = model.predict([list(data.values())])
    return jsonify({"prediction": int(prediction[0])})
