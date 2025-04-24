```python
from flask import Flask, request, jsonify
import os, requests

app = Flask(__name__)
TODOIST_TOKEN = os.getenv("TODOIST_TOKEN")
BASE_URL = "https://api.todoist.com/rest/v2"
HEADERS = lambda: {"Authorization": f"Bearer {TODOIST_TOKEN}"}
JSON_HEADERS = lambda: {**HEADERS(), "Content-Type": "application/json"}

# Health Check
@app.route("/", methods=["GET"])
def home():
    return "✅ GTD Backend Running!"

# ----- TASKS -----
# List active tasks with optional filters
@app.route("/tasks", methods=["GET"])
def get_tasks():
    resp = requests.get(f"{BASE_URL}/tasks", headers=HEADERS(), params=request.args)
    return jsonify(resp.json()), resp.status_code

# Get a single task
@app.route("/tasks/<task_id>", methods=["GET"])
def get_task(task_id):
    resp = requests.get(f"{BASE_URL}/tasks/{task_id}", headers=HEADERS())
    return jsonify(resp.json()), resp.status_code

# Create a new task
@app.route("/tasks", methods=["POST"])
def create_task():
    resp = requests.post(f"{BASE_URL}/tasks", headers=JSON_HEADERS(), json=request.json)
    return jsonify(resp.json()), resp.status_code

# Update an existing task
@app.route("/tasks/<task_id>", methods=["POST"])
def update_task(task_id):
    resp = requests.post(f"{BASE_URL}/tasks/{task_id}", headers=JSON_HEADERS(), json=request.json)
    return jsonify(resp.json()), resp.status_code

# Close (complete) a task
@app.route("/tasks/<task_id>/close", methods=["POST"])
def close_task(task_id):
    resp = requests.post(f"{BASE_URL}/tasks/{task_id}/close", headers=HEADERS())
    return ("", resp.status_code)

# Reopen a completed task
@app.route("/tasks/<task_id>/reopen", methods=["POST"])
def reopen_task(task_id):
    resp = requests.post(f"{BASE_URL}/tasks/{task_id}/reopen", headers=HEADERS())
    return ("", resp.status_code)

# ----- PROJECTS -----
# List all projects
@app.route("/projects", methods=["GET"])
def list_projects():
    resp = requests.get(f"{BASE_URL}/projects", headers=HEADERS())
    return jsonify(resp.json()), resp.status_code

# Get a single project
@app.route("/projects/<project_id>", methods=["GET"])
def get_project(project_id):
    resp = requests.get(f"{BASE_URL}/projects/{project_id}", headers=HEADERS())
    return jsonify(resp.json()), resp.status_code

# Create a new project
@app.route("/projects", methods=["POST"])
def create_project():
    resp = requests.post(f"{BASE_URL}/projects", headers=JSON_HEADERS(), json=request.json)
    return jsonify(resp.json()), resp.status_code

# Update a project
@app.route("/projects/<project_id>", methods=["POST"])
def update_project(project_id):
    resp = requests.post(f"{BASE_URL}/projects/{project_id}", headers=JSON_HEADERS(), json=request.json)
    return jsonify(resp.json()), resp.status_code

# Delete a project
@app.route("/projects/<project_id>", methods=["DELETE"])
def delete_project(project_id):
    resp = requests.delete(f"{BASE_URL}/projects/{project_id}", headers=HEADERS())
    return ("", resp.status_code)

# ----- SECTIONS -----
# List all sections (optionally filter by project_id)
@app.route("/sections", methods=["GET"])
def list_sections():
    resp = requests.get(f"{BASE_URL}/sections", headers=HEADERS(), params=request.args)
    return jsonify(resp.json()), resp.status_code

# Create a section
@app.route("/sections", methods=["POST"])
def create_section():
    resp = requests.post(f"{BASE_URL}/sections", headers=JSON_HEADERS(), json=request.json)
    return jsonify(resp.json()), resp.status_code

# Update a section
@app.route("/sections/<section_id>", methods=["POST"])
def update_section(section_id):
    resp = requests.post(f"{BASE_URL}/sections/{section_id}", headers=JSON_HEADERS(), json=request.json)
    return jsonify(resp.json()), resp.status_code

# Delete a section
@app.route("/sections/<section_id>", methods=["DELETE"])
def delete_section(section_id):
    resp = requests.delete(f"{BASE_URL}/sections/{section_id}", headers=HEADERS())
    return ("", resp.status_code)

# ----- LABELS -----
# List all labels
@app.route("/labels", methods=["GET"])
def list_labels():
    resp = requests.get(f"{BASE_URL}/labels", headers=HEADERS())
    return jsonify(resp.json()), resp.status_code

# Get a single label
@app.route("/labels/<label_id>", methods=["GET"])
def get_label(label_id):
    resp = requests.get(f"{BASE_URL}/labels/{label_id}", headers=HEADERS())
    return jsonify(resp.json()), resp.status_code

# Create a label
@app.route("/labels", methods=["POST"])
def create_label():
    resp = requests.post(f"{BASE_URL}/labels", headers=JSON_HEADERS(), json=request.json)
    return jsonify(resp.json()), resp.status_code

# Update a label
@app.route("/labels/<label_id>", methods=["POST"])
def update_label(label_id):
    resp = requests.post(f"{BASE_URL}/labels/{label_id}", headers=JSON_HEADERS(), json=request.json)
    return jsonify(resp.json()), resp.status_code

# Delete a label
@app.route("/labels/<label_id>", methods=["DELETE"])
def delete_label(label_id):
    resp = requests.delete(f"{BASE_URL}/labels/{label_id}", headers=HEADERS())
    return ("", resp.status_code)

# ----- COMMENTS (NOTES) -----
# List comments by task or project
@app.route("/comments", methods=["GET"])
def list_comments():
    params = {}
    if request.args.get("task_id"): params["task_id"] = request.args.get("task_id")
    if request.args.get("project_id"): params["project_id"] = request.args.get("project_id")
    resp = requests.get(f"{BASE_URL}/comments", headers=HEADERS(), params=params)
    return jsonify(resp.json()), resp.status_code

# Create a comment on a task or project
@app.route("/comments", methods=["POST"])
def create_comment():
    data = request.json
    payload = {"content": data.get("content")}
    if data.get("task_id"): payload["task_id"] = data.get("task_id")
    if data.get("project_id"): payload["project_id"] = data.get("project_id")
    resp = requests.post(f"{BASE_URL}/comments", headers=JSON_HEADERS(), json=payload)
    return jsonify(resp.json()), resp.status_code

# Update a comment
@app.route("/comments/<comment_id>", methods=["POST"])
def update_comment(comment_id):
    data = request.json
    resp = requests.post(f"{BASE_URL}/comments/{comment_id}", headers=JSON_HEADERS(), json={"content": data.get("content")})
    return jsonify(resp.json()), resp.status_code

# Delete a comment
@app.route("/comments/<comment_id>", methods=["DELETE"])
def delete_comment(comment_id):
    resp = requests.delete(f"{BASE_URL}/comments/{comment_id}", headers=HEADERS())
    return ("", resp.status_code)

# ----- REMINDERS -----
# List all reminders
@app.route("/reminders", methods=["GET"])
def list_reminders():
    resp = requests.get(f"{BASE_URL}/reminders", headers=HEADERS())
    return jsonify(resp.json()), resp.status_code

# Create a reminder
@app.route("/reminders", methods=["POST"])
def create_reminder():
    resp = requests.post(f"{BASE_URL}/reminders", headers=JSON_HEADERS(), json=request.json)
    return jsonify(resp.json()), resp.status_code

# Delete a reminder
@app.route("/reminders/<reminder_id>", methods=["DELETE"])
def delete_reminder(reminder_id):
    resp = requests.delete(f"{BASE_URL}/reminders/{reminder_id}", headers=HEADERS())
    return ("", resp.status_code)

# ----- COLLABORATORS -----
# List collaborators in shared projects
@app.route("/collaborators", methods=["GET"])
def list_collaborators():
    resp = requests.get(f"{BASE_URL}/collaborators", headers=HEADERS())
    return jsonify(resp.json()), resp.status_code

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
```
