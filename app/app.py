"""
Task Tracker API — a deliberately small demo service.

This exists as the "patient" for the Docker Deployment Troubleshooting Lab:
a real (if tiny) Flask app with a health check, so the lab can demonstrate
a genuine broken-deployment -> diagnosis -> fix cycle rather than a toy.
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timezone

from flask import Flask, jsonify, request

app = Flask(__name__)

# In-memory store is fine here — this app exists to demonstrate deployment
# and reliability practices, not to be a production task tracker.
TASKS: list[dict] = [
    {"id": 1, "title": "Set up staging environment", "done": True},
    {"id": 2, "title": "Write CI/CD pipeline", "done": True},
    {"id": 3, "title": "Add health checks", "done": False},
]

START_TIME = time.time()


@app.get("/")
def index():
    return jsonify(
        {
            "service": "task-tracker-api",
            "status": "ok",
            "docs": "/health for liveness, /tasks for the task list",
        }
    )


@app.get("/health")
def health():
    """
    Liveness/readiness probe.

    Deliberately checks something real (that TASKS is initialised and the
    process has been up for a moment) rather than always returning 200, so
    the broken-deployment scenario has an honest signal to fail.
    """
    uptime_seconds = round(time.time() - START_TIME, 2)
    healthy = isinstance(TASKS, list)

    body = {
        "status": "healthy" if healthy else "unhealthy",
        "uptime_seconds": uptime_seconds,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "env": os.environ.get("APP_ENV", "development"),
    }
    return jsonify(body), 200 if healthy else 503


@app.get("/tasks")
def list_tasks():
    return jsonify(TASKS)


@app.post("/tasks")
def create_task():
    payload = request.get_json(silent=True) or {}
    title = payload.get("title")
    if not title:
        return jsonify({"error": "title is required"}), 400

    new_id = max((t["id"] for t in TASKS), default=0) + 1
    task = {"id": new_id, "title": title, "done": False}
    TASKS.append(task)
    return jsonify(task), 201


if __name__ == "__main__":
    # Host 0.0.0.0 so the container's port mapping actually works —
    # binding to 127.0.0.1 here is one of the classic "works on my
    # machine, dead in the container" mistakes this lab is built to show.
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
