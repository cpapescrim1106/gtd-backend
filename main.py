import os
from flask import Flask, request, jsonify, Response, send_file
import requests

app = Flask(__name__)

# Serve the OpenAPI spec file
@app.route("/openapi.json")
def serve_openapi():
    # Ensure the openapi.json file is in the same directory as main.py
    # or provide the correct path
    try:
        return send_file("openapi.json", mimetype='application/json')
    except FileNotFoundError:
        return jsonify({"error": "openapi.json not found"}), 404


# Base URL for Todoist’s REST v2 API
TODOIST_API_BASE = "https://api.todoist.com/rest/v2"

def get_todoist_headers():
    """Validates API keys and returns headers for Todoist API calls."""
    # Get the API key provided by the client (e.g., OpenAI Action)
    api_key = request.headers.get("X-API-KEY")
    if not api_key:
        print("Missing X-API-KEY header from incoming request")
        # Don't return 401 here immediately, let the caller handle None
        return None

    # Get the expected API key from environment variables (set in Render)
    expected_api_key = os.getenv("API_KEY")
    if not expected_api_key:
        print("API_KEY environment variable not set on the server")
        return None # Server configuration issue

    # Validate the client's API key against the expected key
    if api_key != expected_api_key:
        print(f"Invalid X-API-KEY provided by client: {api_key}")
        return None # Authentication failure

    # Get the Todoist API Token from environment variables (set in Render)
    todoist_token = os.getenv("TODOIST_API_TOKEN")
    if not todoist_token:
        print("TODOIST_API_TOKEN environment variable not set on the server")
        return None # Server configuration issue

    # Prepare headers for the Todoist API
    headers = {
        "Authorization": f"Bearer {todoist_token}",
        "Content-Type": "application/json"
    }
    # Avoid printing sensitive headers in production logs if possible
    # print(f"Headers prepared for Todoist (Authorization omitted for security)")
    return headers

def proxy(method, path, params=None, json_data=None):
    """Proxies requests to the Todoist API."""
    headers = get_todoist_headers()
    if headers is None:
        # Determine if the error was client-side (bad X-API-KEY) or server-side (missing ENV VARS)
        if not request.headers.get("X-API-KEY") or request.headers.get("X-API-KEY") != os.getenv("API_KEY"):
             return jsonify({"error": "Authentication failed: Invalid or missing X-API-KEY header"}), 401
        else:
             # If X-API-KEY was valid, the issue is likely server config
             print("Server configuration error: Check API_KEY and TODOIST_API_TOKEN environment variables.")
             return jsonify({"error": "Internal server error: Service configuration issue"}), 500


    url = TODOIST_API_BASE + path
    print(f"Sending to Todoist: {method} {url}, Params: {params}, JSON: {json_data}")
    try:
        resp = requests.request(method, url, headers=headers, params=params, json=json_data)
        print(f"Todoist response: Status {resp.status_code}, Body: {resp.text[:500]}...") # Log truncated body

        # Handle successful empty response (204 No Content)
        if resp.status_code == 204:
            return ("", 204)

        # Try to parse JSON, otherwise return raw text
        try:
            body = resp.json()
            # Return JSON response with the original status code
            return jsonify(body), resp.status_code
        except ValueError:
            # If response is not JSON, return it as text
             return Response(resp.text, status=resp.status_code, content_type=resp.headers.get("Content-Type", "text/plain"))

    except requests.exceptions.RequestException as e:
        print(f"Request error connecting to Todoist: {str(e)}")
        return jsonify({"error": f"Failed to connect to Todoist API: {str(e)}"}), 503 # Service Unavailable


@app.route("/tasks/manage", methods=["POST"])
def manage_tasks():
    """Manages task operations based on the 'action' field."""
    data = request.get_json(force=True) # Use force=True cautiously
    action = data.get("action")
    print(f"Tasks manage request received: {data}")

    if not action:
        return jsonify({"error": "'action' field is required"}), 400

    action = action.lower()  # Normalize action to lowercase

    # --- List Tasks ---
    if action == "list":
        params = {}
        for key in ("project_id", "label_id", "filter", "lang"):
            if data.get(key) is not None:
                params[key] = data[key]
        return proxy("GET", "/tasks", params=params)

    # --- Get Task ---
    if action == "get":
        tid = data.get("task_id")
        if not tid:
            return jsonify({"error": "task_id is required for 'get' action"}), 400
        return proxy("GET", f"/tasks/{tid}")

    # --- Create Task ---
    if action == "create":
        payload = {k: data[k] for k in (
            "content", "project_id", "section_id", "parent_id", "order",
            "due_string", "due_date", "due_datetime", "due_lang",
            "priority", "assignee_id", "duration", "duration_unit", "description"  # <-- Added description here
        ) if k in data}

        if "labels" in data:
            if isinstance(data["labels"], list) and all(isinstance(item, str) for item in data["labels"]):
                payload["labels"] = data["labels"]
            else:
                return jsonify({"error": "'labels' must be a list of strings"}), 400

        if "content" not in payload or not payload["content"]:
            return jsonify({"error": "'content' is required to create a task"}), 400

        return proxy("POST", "/tasks", json_data=payload)

    # --- Update Task ---
    if action == "update":
        tid = data.get("task_id")
        if not tid:
            return jsonify({"error": "task_id is required for 'update' action"}), 400

        payload = {k: data[k] for k in (
            "content", "due_string", "due_date", "due_datetime", "due_lang",
            "priority", "assignee_id", "duration", "duration_unit", "description"  # <-- Added description here
        ) if k in data}

        if "labels" in data:
            if isinstance(data["labels"], list) and all(isinstance(item, str) for item in data["labels"]):
                payload["labels"] = data["labels"]
            else:
                return jsonify({"error": "'labels' must be a list of strings"}), 400

        if not payload:
            return jsonify({"error": "At least one field (content, due_*, priority, labels, description, etc.) must be provided for update"}), 400

        return proxy("POST", f"/tasks/{tid}", json_data=payload)

    # --- Delete Task ---
    if action == "delete":
        tid = data.get("task_id")
        if not tid:
            return jsonify({"error": "task_id is required for 'delete' action"}), 400
        return proxy("DELETE", f"/tasks/{tid}")

    # --- Move Task ---
    if action == "move":
        print("Warning: The 'move' action might not work as expected with Todoist REST API v2. Consider using 'update' with project_id/section_id.")
        tid = data.get("task_id")
        if not tid:
            return jsonify({"error": "task_id is required for 'move' action"}), 400

        move_payload = {}
        if "project_id" in data:
            move_payload["project_id"] = data["project_id"]
        if "section_id" in data:
            move_payload["section_id"] = data["section_id"]

        if not move_payload:
            return jsonify({"error": "Either 'project_id' or 'section_id' is required for 'move' action"}), 400

        return proxy("POST", f"/tasks/{tid}", json_data=move_payload)

    # --- Change Task Status (Close/Reopen) ---
    if action == "status":
        tid = data.get("task_id")
        status = data.get("status", "").lower()
        if not tid:
            return jsonify({"error": "task_id is required for 'status' action"}), 400
        if status not in ("closed", "open"):
            return jsonify({"error": "status ('closed' or 'open') is required for 'status' action"}), 400

        endpoint = "close" if status == "closed" else "reopen"
        return proxy("POST", f"/tasks/{tid}/{endpoint}")

    # --- Unknown Action ---
    return jsonify({"error": f"Unknown or unsupported action '{data.get('action')}' for tasks"}), 400


# --- Project Management ---
@app.route("/projects/manage", methods=["POST"])
def manage_projects():
    data = request.get_json(force=True)
    action = data.get("action", "").lower()
    print(f"Projects manage request received: {data}")

    if not action:
         return jsonify({"error": "'action' field is required"}), 400

    if action == "list":
        return proxy("GET", "/projects")

    if action == "get":
        pid = data.get("project_id")
        if not pid:
            return jsonify({"error": "project_id is required for 'get' action"}), 400
        return proxy("GET", f"/projects/{pid}")

    if action == "create":
        payload = {k: data[k] for k in ("name", "color", "parent_id", "is_favorite", "view_style") if k in data}
        if "name" not in payload or not payload["name"]:
             return jsonify({"error": "'name' is required to create a project"}), 400
        return proxy("POST", "/projects", json_data=payload)

    if action == "update":
        pid = data.get("project_id")
        if not pid:
            return jsonify({"error": "project_id is required for 'update' action"}), 400
        # Note: is_shared cannot be updated via API after creation
        payload = {k: data[k] for k in ("name", "color", "is_favorite", "view_style") if k in data}
        if not payload:
             return jsonify({"error": "At least one field (name, color, is_favorite, view_style) must be provided for update"}), 400
        return proxy("POST", f"/projects/{pid}", json_data=payload)

    if action == "delete":
        pid = data.get("project_id")
        if not pid:
            return jsonify({"error": "project_id is required for 'delete' action"}), 400
        return proxy("DELETE", f"/projects/{pid}")

    # Note: Archive/Unarchive are not distinct actions in REST v2.
    # It's handled by updating the project (is_archived is read-only).
    # Shared projects are managed via sharing endpoints, not a simple 'state'.
    # Removing 'state' action as it doesn't map directly to REST v2 in this way.
    # if action == "state": ... (Removed)

    if action == "collaborators":
        pid = data.get("project_id")
        # Listing collaborators requires a project ID
        if not pid:
             return jsonify({"error": "project_id is required for 'collaborators' action"}), 400
        return proxy("GET", f"/projects/{pid}/collaborators")

    return jsonify({"error": f"Unknown or unsupported action '{data.get('action')}' for projects"}), 400


# --- Section Management ---
@app.route("/sections/manage", methods=["POST"])
def manage_sections():
    data = request.get_json(force=True)
    action = data.get("action", "").lower()
    print(f"Sections manage request received: {data}")

    if not action:
         return jsonify({"error": "'action' field is required"}), 400

    if action == "list":
        params = {}
        if data.get("project_id"):
            params["project_id"] = data["project_id"]
        return proxy("GET", "/sections", params=params) # Can list all sections or by project_id

    if action == "get":
        sid = data.get("section_id")
        if not sid:
            return jsonify({"error": "section_id is required for 'get' action"}), 400
        return proxy("GET", f"/sections/{sid}")

    if action == "create":
        payload = {k: data[k] for k in ("project_id", "name", "order") if k in data}
        if "name" not in payload or not payload["name"]:
             return jsonify({"error": "'name' is required to create a section"}), 400
        if "project_id" not in payload or not payload["project_id"]:
             return jsonify({"error": "'project_id' is required to create a section"}), 400
        return proxy("POST", "/sections", json_data=payload)

    if action == "update":
        sid = data.get("section_id")
        if not sid:
            return jsonify({"error": "section_id is required for 'update' action"}), 400
        payload = {k: data[k] for k in ("name", "order") if k in data} # Only name and order are updatable
        if not payload:
             return jsonify({"error": "At least one field (name, order) must be provided for update"}), 400
        if "name" in payload and not payload["name"]:
             return jsonify({"error": "'name' cannot be empty for update"}), 400
        return proxy("POST", f"/sections/{sid}", json_data=payload)

    if action == "delete":
        sid = data.get("section_id")
        if not sid:
            return jsonify({"error": "section_id is required for 'delete' action"}), 400
        return proxy("DELETE", f"/sections/{sid}")

    return jsonify({"error": f"Unknown action '{data.get('action')}' for sections"}), 400


# --- Label Management ---
@app.route("/labels/manage", methods=["POST"])
def manage_labels():
    # Manages personal labels
    data = request.get_json(force=True)
    action = data.get("action", "").lower()
    print(f"Labels manage request received: {data}")

    if not action:
         return jsonify({"error": "'action' field is required"}), 400

    # --- Personal Label Actions ---
    if action == "list":
        return proxy("GET", "/labels") # Gets personal labels

    if action == "get":
        # Todoist uses string IDs for labels in URLs, but might return numeric IDs in objects. Be consistent.
        lid = data.get("label_id") # Expect string ID from request as per typical REST patterns
        if not lid:
            return jsonify({"error": "label_id (string) is required for 'get' action"}), 400
        return proxy("GET", f"/labels/{lid}")

    if action == "create":
        payload = {k: data[k] for k in ("name", "color", "order", "is_favorite") if k in data}
        if "name" not in payload or not payload["name"]:
             return jsonify({"error": "'name' is required to create a label"}), 400
        return proxy("POST", "/labels", json_data=payload)

    if action == "update":
        lid = data.get("label_id")
        if not lid:
            return jsonify({"error": "label_id (string) is required for 'update' action"}), 400
        payload = {k: data[k] for k in ("name", "color", "order", "is_favorite") if k in data}
        if not payload:
             return jsonify({"error": "At least one field (name, color, order, is_favorite) must be provided for update"}), 400
        return proxy("POST", f"/labels/{lid}", json_data=payload)

    if action == "delete":
        lid = data.get("label_id")
        if not lid:
            return jsonify({"error": "label_id (string) is required for 'delete' action"}), 400
        return proxy("DELETE", f"/labels/{lid}")

    # --- Shared Label Actions (These are different in REST v2) ---
    # REST v2 doesn't have these exact endpoints. Shared labels are viewed via GET /labels.
    # Renaming/removing applies to personal labels only via the update/delete actions above.
    # Removing shared-specific actions as they don't map directly.
    # if action == "list_shared": ... (Removed)
    # if action == "rename_shared": ... (Removed)
    # if action == "remove_shared": ... (Removed)

    return jsonify({"error": f"Unknown or unsupported action '{data.get('action')}' for labels"}), 400


# --- Comment Management ---
@app.route("/comments/manage", methods=["POST"])
def manage_comments():
    data = request.get_json(force=True)
    action = data.get("action", "").lower()
    print(f"Comments manage request: {data}")

    if not action:
         return jsonify({"error": "'action' field is required"}), 400

    if action == "list":
        params = {}
        # Must provide either task_id or project_id
        if data.get("task_id"):
            params["task_id"] = data["task_id"]
        elif data.get("project_id"):
             params["project_id"] = data["project_id"]
        else:
            return jsonify({"error": "Either 'task_id' or 'project_id' is required for 'list' action"}), 400
        return proxy("GET", "/comments", params=params)

    if action == "get":
        cid = data.get("comment_id")
        if not cid:
            return jsonify({"error": "comment_id is required for 'get' action"}), 400
        return proxy("GET", f"/comments/{cid}")

    if action == "create":
        payload = {k: data[k] for k in ("content", "task_id", "project_id", "attachment") if k in data}
        # Attachment needs special handling (file upload), not covered here simply.
        if "attachment" in payload:
             print("Warning: Simple JSON proxy cannot handle file attachments for comments.")
             del payload["attachment"] # Remove attachment if just passing JSON
        if "content" not in payload or not payload["content"]:
             return jsonify({"error": "'content' is required to create a comment"}), 400
        if not ("task_id" in payload or "project_id" in payload):
            return jsonify({"error": "Either 'task_id' or 'project_id' is required for 'create' action"}), 400
        return proxy("POST", "/comments", json_data=payload)

    if action == "update":
        cid = data.get("comment_id")
        if not cid:
            return jsonify({"error": "comment_id is required for 'update' action"}), 400
        content = data.get("content")
        if not content:
            return jsonify({"error": "'content' is required for 'update' action"}), 400
        return proxy("POST", f"/comments/{cid}", json_data={"content": content}) # Only content is updatable

    if action == "delete":
        cid = data.get("comment_id")
        if not cid:
            return jsonify({"error": "comment_id is required for 'delete' action"}), 400
        return proxy("DELETE", f"/comments/{cid}")

    return jsonify({"error": f"Unknown action '{data.get('action')}' for comments"}), 400


# --- Reminder Management (Not standard in REST v2 like this) ---
# Reminders are part of the Task object's 'due' field or handled by integrations.
# This endpoint likely won't work as intended with REST v2.
# Removing this endpoint as it doesn't map cleanly.
# @app.route("/reminders/manage", methods=["POST"]) ... (Removed)


# --- Collaborator Management (Simplified) ---
# This endpoint primarily lists collaborators for a specific project.
@app.route("/collaborators/manage", methods=["POST"])
def manage_collaborators():
    data = request.get_json(force=True)
    action = data.get("action", "").lower()
    print(f"Collaborators manage request: {data}")

    if action != "list":
        return jsonify({"error": "Only 'list' action is supported for collaborators via this endpoint"}), 400

    pid = data.get("project_id")
    # Listing collaborators requires a project ID in REST v2
    if not pid:
         return jsonify({"error": "project_id is required for 'list' collaborators action"}), 400

    return proxy("GET", f"/projects/{pid}/collaborators")


# --- Debug Endpoint (Example) ---
@app.route("/debug/labels", methods=["GET"])
def debug_labels():
    """Endpoint to fetch all personal labels for debugging."""
    print("Debug: Received request for /debug/labels")
    headers = get_todoist_headers()
    if headers is None:
         # Check if the error is client-side authentication or server-side config
        if not request.headers.get("X-API-KEY") or request.headers.get("X-API-KEY") != os.getenv("API_KEY"):
             return jsonify({"error": "Authentication failed: Invalid or missing X-API-KEY header"}), 401
        else:
             return jsonify({"error": "Internal server error: Service configuration issue"}), 500

    url = f"{TODOIST_API_BASE}/labels"
    print(f"Debug: Sending GET request to {url}")
    try:
        resp = requests.get(url, headers=headers)
        print(f"Debug labels Todoist response: Status {resp.status_code}, Body: {resp.text[:200]}...")
        status_code = resp.status_code
        try:
             body = resp.json()
        except ValueError:
             body = resp.text
        # Return a standard JSON structure for the debug endpoint
        return jsonify({
            "status_code_from_todoist": status_code,
            "response_body": body
        }), 200 # Always return 200 from this debug endpoint itself, showing the result
    except requests.exceptions.RequestException as e:
        print(f"Debug labels error: {str(e)}")
        return jsonify({"error": f"Debug request failed: {str(e)}"}), 500


if __name__ == "__main__":
    # Set default port to 10000, suitable for Render deployment
    port = int(os.environ.get("PORT", 10000))
    # Run on 0.0.0.0 to be accessible externally
    app.run(host="0.0.0.0", port=port)