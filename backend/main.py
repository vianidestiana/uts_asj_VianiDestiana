from flask import Flask, jsonify
import requests

app = Flask(__name__)

API_URL = "http://api:8000"

@app.route("/")
def home():
    return "Backend Running"

@app.route("/users")
def users():
    res = requests.get(f"{API_URL}/users")
    return jsonify(res.json())

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
