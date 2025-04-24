from flask import Flask, request, jsonify
import os, requests

app = Flask(__name__)
TODOIST_TOKEN = os.getenv("TODOIST_TOKEN")

@app.route("/")
def home():
    return "✅ GTD Backend Running!"

@app.route("/tasks", methods=["GET"])
def get_tasks():
    headers = {"Authorization": f"Bearer {TODOIST_TOKEN}"}
    resp = requests.get("https://api.todoist.com/rest/v2/tasks", headers=headers)
    return jsonify(resp.json()), resp.status_code

@app.route("/task", methods=["POST"])
def create_task():
    data = request.json
    headers = {
        "Authorization": f"Bearer {TODOIST_TOKEN}",
        "Content-Type": "application/json"
    }
    resp = requests.post("https://api.todoist.com/rest/v2/tasks", headers=headers, json=data)
    return jsonify(resp.json()), resp.status_code

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
