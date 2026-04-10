# app.py — Flask backend (no SSE, simple REST API)

import os, json, sys
from flask import Flask, render_template, jsonify, request
from dotenv import load_dotenv

from agents.environment import EmailEnvironment
from agents.classifier  import EmailClassifierAgent
from data.emails        import EMAILS
from data.prompts       import REWARD_TABLES

load_dotenv()

app   = Flask(__name__)
env   = EmailEnvironment()
agent = None


def get_agent():
    global agent
    key = (os.getenv("API_KEY") or os.getenv("HF_TOKEN") or
           os.getenv("ANTHROPIC_API_KEY", "")).strip()
    base_url = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
    if agent is None:
        agent = EmailClassifierAgent(api_key=key, base_url=base_url)
    return agent


@app.route("/")
def index():
    return render_template("index.html", emails=EMAILS)


@app.route("/api/reset", methods=["POST"])
@app.route("/reset", methods=["POST"])
def reset():
    env.reset()
    return jsonify({
        "observation": env.get_state(),
        "reward": 0.0,
        "done": False,
        "info": {}
    })
# @app.route("/reset", methods=["POST"])
# def reset():
#     env.reset()
#     return jsonify({"ok": True, "state": env.get_state()})


@app.route("/api/state")
@app.route("/state")
def state():
    return jsonify(env.get_state())


@app.route("/api/rewards/<level>")
def reward_table(level):
    return jsonify(REWARD_TABLES.get(level, REWARD_TABLES["easy"]))


@app.route("/api/check")
def check():
    key = (os.getenv("API_KEY") or os.getenv("HF_TOKEN") or os.getenv("ANTHROPIC_API_KEY", "")).strip()
    ok  = bool(key and key != "your_api_key_here")
    return jsonify({"server": "ok", "api_key_set": ok,
                    "preview": key[:14]+"..." if ok else "NOT SET"})


@app.route("/api/step", methods=["POST"])
@app.route("/step", methods=["POST"])
def step():
    data  = request.get_json()
    level = data.get("level", "easy")
    idx   = data.get("email_index", 0)

    if idx >= len(EMAILS):
        return jsonify({
            "observation": env.get_state(),
            "reward": 0.0,
            "done": True,
            "info": {}
        })

    email = EMAILS[idx]

    try:
        classifier = get_agent()
        action = classifier.classify(email, level)
    except Exception:
        action = {"label": "fallback"}

    result = env.step(action, level)

    return jsonify({
        "observation": env.get_state(),
        "reward": result["reward"],
        "done": False,
        "info": result.get("info", {})
    })
# @app.route("/step", methods=["POST"])
# def step():
#     """
#     Process ONE email step.
#     Frontend calls this for each email one-by-one.
#     Body: { "level": "easy"|"medium"|"hard", "email_index": 0..4 }
#     """
#     data  = request.get_json()
#     level = data.get("level", "easy")
#     idx   = data.get("email_index", 0)

#     # validate
#     if idx >= len(EMAILS):
#         return jsonify({"error": "No more emails"}), 400

#     email = EMAILS[idx]

#     try:
#         classifier = get_agent()
#         action     = classifier.classify(email, level)
#     except ValueError as e:
#         return jsonify({"error": str(e)}), 400
#     except Exception as e:
#         # API error — return fallback, don't crash
#         action = ({"category":"work","priority":"medium",
#                    "action":"reply","reason":"API error fallback"}
#                   if level == "hard"
#                   else {"label":"work","reason":"API error fallback"})

#     result = env.step(action, level)

#     return jsonify({
#         "email":     email,
#         "action":    action,
#         "reward":    result["reward"],
#         "correct":   result["info"]["step_record"]["correct"],
#         "breakdown": result["info"]["step_record"]["breakdown"],
#         "state":     env.get_state(),
#     })


def startup_check():
    print("\n  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  ⚡ Email Classifier Agent")
    print("  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    key = (os.getenv("API_KEY") or os.getenv("HF_TOKEN") or
           os.getenv("ANTHROPIC_API_KEY", "")).strip()
    base_url = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
    print(f"\n  ✓ API Key  : {key[:14]}..." if key else "\n  ⚠ API Key  : not set (using fallback)")
    print(f"  ✓ Base URL : {base_url}")
    port = 7860
    print(f"  ✓ Server   : http://localhost:{port}")
    print("  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
    return port


if __name__ == "__main__":
    # port = startup_check()
    port = 7860
    # app.run(debug=False, port=port, threaded=True)
    app.run(host="0.0.0.0", port=7860, debug=False, threaded=True)
