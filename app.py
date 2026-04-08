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
    key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not key or key == "your_api_key_here":
        raise ValueError("ANTHROPIC_API_KEY .env mein set nahi hai!")
    if agent is None:
        agent = EmailClassifierAgent(api_key=key)
    return agent


@app.route("/")
def index():
    return render_template("index.html", emails=EMAILS)


@app.route("/api/reset", methods=["POST"])
def reset():
    env.reset()
    return jsonify({"ok": True, "state": env.get_state()})


@app.route("/api/state")
def state():
    return jsonify(env.get_state())


@app.route("/api/rewards/<level>")
def reward_table(level):
    return jsonify(REWARD_TABLES.get(level, REWARD_TABLES["easy"]))


@app.route("/api/check")
def check():
    key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    ok  = bool(key and key != "your_api_key_here")
    return jsonify({"server": "ok", "api_key_set": ok,
                    "preview": key[:14]+"..." if ok else "NOT SET"})


@app.route("/api/step", methods=["POST"])
def step():
    """
    Process ONE email step.
    Frontend calls this for each email one-by-one.
    Body: { "level": "easy"|"medium"|"hard", "email_index": 0..4 }
    """
    data  = request.get_json()
    level = data.get("level", "easy")
    idx   = data.get("email_index", 0)

    # validate
    if idx >= len(EMAILS):
        return jsonify({"error": "No more emails"}), 400

    email = EMAILS[idx]

    try:
        classifier = get_agent()
        action     = classifier.classify(email, level)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        # API error — return fallback, don't crash
        action = ({"category":"work","priority":"medium",
                   "action":"reply","reason":"API error fallback"}
                  if level == "hard"
                  else {"label":"work","reason":"API error fallback"})

    result = env.step(action, level)

    return jsonify({
        "email":     email,
        "action":    action,
        "reward":    result["reward"],
        "correct":   result["info"]["step_record"]["correct"],
        "breakdown": result["info"]["step_record"]["breakdown"],
        "state":     env.get_state(),
    })


def startup_check():
    print("\n  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  ⚡ Email Classifier Agent")
    print("  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    key = os.getenv("ANTHROPIC_API_KEY","").strip()
    if not key or key == "your_api_key_here":
        print("\n  ❌ ERROR: API key .env mein nahi hai!")
        print("     ANTHROPIC_API_KEY=sk-ant-... daalo\n")
        sys.exit(1)
    print(f"\n  ✓ API Key : {key[:14]}...")
    port = int(os.getenv("FLASK_PORT", 5000))
    print(f"  ✓ Server  : http://localhost:{port}")
    print("  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
    return port


if __name__ == "__main__":
    port = startup_check()
    app.run(debug=False, port=port, threaded=True)
