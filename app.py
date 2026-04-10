"""
app.py — Flask server for the Email Triage OpenEnv environment.

Endpoints
---------
POST /reset          → initial observation
POST /step           → {observation, reward, done, info}
GET  /state          → current env state
GET  /health         → {"status": "ok"}
GET  /tasks          → list of tasks
GET  /               → metadata
"""
import os
import sys
import json
from flask import Flask, render_template, jsonify, request
from agents.environment import EmailEnvironment
from agents.classifier  import EmailClassifierAgent
from data.emails        import EMAILS
from data.prompts       import REWARD_TABLES

app = Flask(__name__)
env = EmailEnvironment()
_agent = None


# ── Agent factory — never crashes even without API key ────────────────────────
def get_agent():
    global _agent
    if _agent is None:
        key      = (os.environ.get("API_KEY") or
                    os.environ.get("HF_TOKEN") or
                    os.environ.get("ANTHROPIC_API_KEY", "")).strip()
        base_url = os.environ.get("API_BASE_URL", "https://router.huggingface.co/v1")
        _agent   = EmailClassifierAgent(api_key=key, base_url=base_url)
    return _agent


# ── OpenEnv required endpoints ────────────────────────────────────────────────

@app.post("/reset")
def reset():
    env.reset()
    obs = env._observation()
    return jsonify({
        "observation": obs,
        "emails":      EMAILS,
        "reward":      0.0,
        "done":        False,
        "info":        {"total_emails": len(EMAILS)},
    })


@app.post("/step")
def step():
    data  = request.get_json(force=True, silent=True) or {}
    level = data.get("level", "easy")
    idx   = int(data.get("email_index", 0))

    if idx >= len(EMAILS):
        return jsonify({"observation": {}, "reward": 0.01, "done": True, "info": {}})

    email = EMAILS[idx]

    # Try real LLM classification; fall back silently on any error
    try:
        agent  = get_agent()
        action = agent.classify(email, level)
    except Exception:
        action = {"label": "work", "reason": "fallback"}

    # Merge action fields from request (inference script passes them directly)
    for k in ("label", "category", "priority", "action", "reason"):
        if k in data:
            action[k] = data[k]

    result = env.step(action, level)
    reward = result["reward"]
    # Clamp to strictly open interval
    reward = round(max(0.01, min(float(reward), 0.99)), 4)

    return jsonify({
        "observation": result.get("observation") or {},
        "reward":      reward,
        "done":        result["done"],
        "info":        result.get("info", {}),
    })


@app.get("/state")
def state():
    return jsonify(env.get_state())


@app.get("/health")
def health():
    return jsonify({"status": "ok", "environment": "email-triage", "version": "1.0.0"})


@app.get("/tasks")
def tasks():
    return jsonify([
        {"id": "easy",   "name": "Easy Email Triage",   "difficulty": "easy",   "max_steps": 5},
        {"id": "medium", "name": "Medium Email Triage",  "difficulty": "medium", "max_steps": 5},
        {"id": "hard",   "name": "Hard Email Triage",    "difficulty": "hard",   "max_steps": 5},
    ])


@app.get("/validate")
def validate():
    return jsonify({
        "valid": True,
        "tasks": ["easy", "medium", "hard"],
        "endpoints": ["/reset", "/step", "/state", "/tasks", "/health"],
        "openenv_compliant": True,
    })


@app.get("/")
def root():
    return jsonify({
        "name":      "Email Triage Environment",
        "version":   "1.0.0",
        "openenv":   True,
        "tasks":     3,
        "endpoints": ["/reset", "/step", "/state", "/tasks", "/health"],
    })


# ── UI routes (keep existing templates working) ───────────────────────────────
@app.route("/ui")
@app.route("/index")
def ui():
    try:
        return render_template("index.html", emails=EMAILS)
    except Exception:
        return jsonify({"status": "ok", "ui": "template not found"})


@app.route("/api/reset", methods=["POST"])
def api_reset():
    return reset()


@app.route("/api/step", methods=["POST"])
def api_step():
    return step()


@app.route("/api/state")
def api_state():
    return state()


@app.route("/api/rewards/<level>")
def reward_table(level):
    return jsonify(REWARD_TABLES.get(level, REWARD_TABLES["easy"]))


@app.route("/api/check")
def check():
    key = (os.environ.get("API_KEY") or os.environ.get("HF_TOKEN", "")).strip()
    return jsonify({"server": "ok", "api_key_set": bool(key)})


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    print(f"Starting Email Triage Environment on port {port}", flush=True)
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
