import os
from flask import Flask, request, jsonify, Response
import requests

app = Flask(__name__)

# Base URL for Todoist’s REST v2 API
TODOIST_API_BASE = "https://api.todoist.com/rest/v2"

def get_todoist_headers():
    api_key = request.headers.get("X-API-KEY")
    if not api_key:
        return None
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    print(f"Headers sent to Todoist: {headers}")  # Log for debugging
    return headers

def proxy(method, path, params=None, json_data=None):
    """
    Forward a request to Todoist, then return its response.
    Handles JSON vs. no-content automatically.
    """
    headers = get_todoist_headers()
    if headers is None:
        return jsonify({"error": "Missing X-API-KEY header"}), 401

    url = TODOIST_API_BASE + path
    print(f"Sending to Todoist: {method} {url}, Params: {params}, JSON: {json_data}")  # Log request
    resp = requests.request(method, url, headers=headers, params=params, json=json_data)
    print(f"Todoist response: Status {resp.status_code}, Body: {resp.text}")  # Log response

    try:
        body = resp.json()
        return jsonify(body), resp.status_code
    except ValueError:
        if resp.status_code == 204:
            return ("", 204)
        return Response(resp.text, status=resp.status_code, content_type=resp.headers.get("Content-Type", "text/plain"))

# ─── Tasks ─────────────────────────────────────────────────────────────────────

@app.route("/tasks/manage", methods=["POST"])
def manage_tasks():
    data = request.get_json(force=True)
    action = data.get("action")
    print(f"Tasks manage request: {data}")  # Log incoming request

    if action == "list":
        params = {}
        for key in ("project_id", "label_id", "filter"):
            if data.get(key) is not None:
                params[key] = data[key]
        return proxy("GET", "/tasks", params=params)

    if action == "get":
        tid = data.get("task_id")
        if not tid:
            return jsonify({"error": "task_id is required"}), 400
        return proxy("GET", f"/tasks/{tid}")

    if action == "create":
        payload = {k: data[k] for k in ("content", "project_id", "section_id", "due_string", "priority", "label_ids") if k in data}
        return proxy("POST", "/tasks", json_data=payload)

    if action == "update":
        tid = data.get("task_id")
        if not tid:
            return jsonify({"error": "task_id is required"}), 400
        payload = {k: data[k] for k in ("content", "due_string", "priority", "label_ids") if k in data}
        return proxy("POST", f"/tasks/{tid}", json_data=payload)

    if action == "delete":
        tid = data.get("task_id")
        if not tid:
            return jsonify({"error": "task_id is required"}), 400
        return proxy("DELETE", f"/tasks/{tid}")

    if action == "move":
        tid = data.get("task_id")
        if not tid:
            return jsonify({"error": "task_id is required"}), 400
        payload = {}
        if "project_id" in data:
            payload["project_id"] = data["project_id"]
        if "section_id" in data:
            payload["section_id"] = data["section_id"]
        return proxy("POST", f"/tasks/{tid}/move", json_data=payload)

    if action == "status":
        tid = data.get("task_id")
        status = data.get("status")
        if not tid or status not in ("closed", "open"):
            return jsonify({"error": "task_id and status ('closed'|'open') are required"}), 400
        endpoint = "close" if status == "closed" else "reopen"
        return proxy("POST", f"/tasks/{tid}/{endpoint}")

    return jsonify({"error": f"Unknown action '{action}'"}), 400

# ─── Projects ──────────────────────────────────────────────────────────────────

@app.route("/projects/manage", methods=["POST"])
def manage_projects():
    data = request.get_json(force=True)
    action = data.get("action")
    print(f"Projects manage request: {data}")  # Log incoming request

    if action == "list":
        return proxy("GET", "/projects")

    if action == "get":
        pid = data.get("project_id")
        if not pid:
            return jsonify({"error": "project_id is required"}), 400
        return proxy("GET", f"/projects/{pid}")

    if action == "create":
        payload = {k: data[k] for k in ("name", "color", "parent_id", "is_shared", "is_favorite") if k in data}
        return proxy("POST", "/projects", json_data=payload)

    if action == "update":
        pid = data.get("project_id")
        if not pid:
            return jsonify({"error": "project_id is required"}), 400
        payload = {k: data[k] for k in ("name", "color", "order", "is_shared", "is_favorite") if k in data}
        return proxy("POST", f"/projects/{pid}", json_data=payload)

    if action == "delete":
        pid = data.get("project_id")
        if not pid:
            return jsonify({"error": "project_id is required"}), 400
        return proxy("DELETE", f"/projects/{pid}")

    if action == "state":
        pid = data.get("project_id")
        state = data.get("state")
        if not pid or state not in ("archived", "active"):
            return jsonify({"error": "project_id and state ('archived'|'active') are required"}), 400
        endpoint = "archive" if state == "archived" else "unarchive"
        return proxy("POST", f"/projects/{pid}/{endpoint}")

    if action == "collaborators":
        pid = data.get("project_id")
        path = f"/projects/{pid}/collaborators" if pid else "/collaborators"
        return proxy("GET", path)

    return jsonify({"error": f"Unknown action '{action}'"}), 400

# ─── Sections ─────────────────────────────────────────────────────────────────

@app.route("/sections/manage", methods=["POST"])
def manage_sections():
    data = request.get_json(force=True)
    action = data.get("action")
    print(f"Sections manage request: {data}")  # Log incoming request

    if action == "list":
        params = {}
        if data.get("project_id"):
            params["project_id"] = data["project_id"]
        return proxy("GET", "/sections", params=params)

    if action == "get":
        sid = data.get("section_id")
        if not sid:
            return jsonify({"error": "section_id is required"}), 400
        return proxy("GET", f"/sections/{sid}")

    if action == "create":
        payload = {"project_id": data.get("project_id"), "name": data.get("name")}
        return proxy("POST", "/sections", json_data=payload)

    if action == "update":
        sid = data.get("section_id")
        if not sid:
            return jsonify({"error": "section_id is required"}), 400
        payload = {k: data[k] for k in ("name", "order") if k in data}
        return proxy("POST", f"/sections/{sid}", json_data=payload)

    if action == "delete":
        sid = data.get("section_id")
        if not sid:
            return jsonify({"error": "section_id is required"}), 400
        return proxy("DELETE", f"/sections/{sid}")

    return jsonify({"error": f"Unknown action '{action}'"}), 400

# ─── Labels ───────────────────────────────────────────────────────────────────

@app.route("/labels/manage", methods=["POST"])
def manage_labels():
    data = request.get_json(force=True)
    action = data.get("action")
    print(f"Labels manage request: {data}")  # Log incoming request

    if action == "list":
        return proxy("GET", "/labels")
    if action == "get":
        lid = data.get("label_id")
        if not lid:
            return jsonify({"error": "label_id is required"}), 400
        return proxy("GET", f"/labels/{lid}")
    if action == "create":
        payload = {k: data[k] for k in ("name", "color", "order", "is_favorite") if k in data}
        return proxy("POST", "/labels", json_data=payload)
    if action == "update":
        lid = data.get("label_id")
        if not lid:
            return jsonify({"error": "label_id is required"}), 400
        payload = {k: data[k] for k in ("name", "color", "order", "is_favorite") if k in data}
        return proxy("POST", f"/labels/{lid}", json_data=payload)
    if action == "delete":
        lid = data.get("label_id")
        if not lid:
            return jsonify({"error": "label_id is required"}), 400
        return proxy("DELETE", f"/labels/{lid}")

    if action == "list_shared":
        return proxy("GET", "/labels/shared")
    if action == "rename_shared":
        name = data.get("name")
        new = data.get("new_name")
        return proxy("POST", "/labels/shared/rename", json_data={"name": name, "new_name": new})
    if action == "remove_shared":
        name = data.get("name")
        return proxy("POST", "/labels/shared/remove", json_data={"name": name})

    return jsonify({"error": f"Unknown action '{action}'"}), 400

# ─── Comments ─────────────────────────────────────────────────────────────────

@app.route("/comments/manage", methods=["POST"])
def manage_comments():
    data = request.get_json(force=True)
    action = data.get("action")
    print(f"Comments manage request: {data}")  # Log incoming request

    if action == "list":
        params = {}
        for key in ("task_id", "project_id"):
            if data.get(key) is not None:
                params[key] = data[key]
        return proxy("GET", "/comments", params=params)

    if action == "get":
        cid = data.get("comment_id")
        if not cid:
            return jsonify({"error": "comment_id is required"}), 400
        return proxy("GET", f"/comments/{cid}")

    if action == "create":
        payload = {k: data[k] for k in ("content", "task_id", "project_id") if k in data}
        return proxy("POST", "/comments", json_data=payload)

    if action == "update":
        cid = data.get("comment_id")
        if not cid:
            return jsonify({"error": "comment_id is required"}), 400
        return proxy("POST", f"/comments/{cid}", json_data={"content": data.get("content")})

    if action == "delete":
        cid = data.get("comment_id")
        if not cid:
            return jsonify({"error": "comment_id is required"}), 400
        return proxy("DELETE", f"/comments/{cid}")

    return jsonify({"error": f"Unknown action '{action}'"}), 400

# ─── Reminders ────────────────────────────────────────────────────────────────

@app.route("/reminders/manage", methods=["POST"])
def manage_reminders():
    data = request.get_json(force=True)
    action = data.get("action")
    print(f"Reminders manage request: {data}")  # Log incoming request

    if action == "list":
        return proxy("GET", "/reminders")

    if action == "create":
        payload = {k: data[k] for k in ("task_id", "due_string") if k in data}
        return proxy("POST", "/reminders", json_data=payload)

    if action == "delete":
        rid = data.get("reminder_id")
        if not rid:
            return jsonify({"error": "reminder_id is required"}), 400
        return proxy("DELETE", f"/reminders/{rid}")

    return jsonify({"error": f"Unknown action '{action}'"}), 400

# ─── Collaborators ─────────────────────────────────────────────────────────────

@app.route("/collaborators/manage", methods=["POST"])
def manage_collaborators():
    data = request.get_json(force=True)
    print(f"Collaborators manage request: {data}")  # Log incoming request
    if data.get("action") != "list":
        return jsonify({"error": "Unknown action, only 'list' is supported"}), 400

    pid = data.get("project_id")
    path = f"/projects/{pid}/collaborators" if pid else "/collaborators"
    return proxy("GET", path)

# ─── Bootstrapping ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)