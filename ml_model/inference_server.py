import joblib, flask, numpy as np
app = flask.Flask(__name__)
model = joblib.load("model.pkl")

# ---- SageMaker health check ----
@app.route("/ping", methods=["GET"])
def ping():
    return "", 200

# ---- SageMaker default invoke ----
@app.route("/invocations", methods=["POST"])
def invoke():
    data = np.array(flask.request.json["features"])
    preds = model.predict([data]).tolist()
    return {"prediction": preds}

# (optional) पुराना predict path
@app.route("/predict", methods=["POST"])
def predict():
    return invoke()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
