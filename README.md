---
title: Email Triage Agent
emoji: 📧
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
tags:
  - openenv
---

# Email Classifier Agent 🤖

AI-powered email classification system using Reinforcement Learning concepts,
Claude API, Flask backend, and a dark industrial UI.

---

## File Structure

```
email_classifier/
│
├── app.py                    # Flask app — routes, SSE stream
│
├── agents/
│   ├── __init__.py
│   ├── classifier.py         # Claude API agent
│   └── environment.py        # RL environment (state, step, reset)
│
├── data/
│   ├── __init__.py
│   ├── emails.py             # Sample emails + ground truth
│   └── prompts.py            # Prompt templates + reward tables
│
├── utils/
│   ├── __init__.py
│   └── reward.py             # Reward calculation (RL concept)
│
├── templates/
│   └── index.html            # Jinja2 HTML template
│
├── static/
│   ├── css/style.css         # Full dark UI stylesheet
│   └── js/app.js             # SSE client + UI logic
│
├── .env.example              # Environment variables template
├── requirements.txt          # Python dependencies
└── README.md
```

---

🚀 Overview

Email Triage OpenEnv is a real-world simulation environment where an AI agent learns to manage and classify emails efficiently using the standard step(), reset(), and state() APIs.

The environment mimics a real inbox where incoming emails must be:

Classified into categories
Assigned appropriate priority levels

This project is designed to evaluate how well an AI agent can automate email handling tasks similar to those performed in real workplace scenarios.

🎯 Motivation

Managing emails is a common real-world task across industries. Automating email triage improves:

Productivity
Response time
Decision-making efficiency

This environment provides a structured way to train and evaluate AI agents on this task.

🧠 Environment Design
🔍 Observation Space

Each step provides the agent with an email:

{
  "email_id": 1,
  "subject": "Meeting at 10 AM",
  "sender": "manager@company.com",
  "content": "Please attend the meeting at 10 AM."
}
⚡ Action Space

The agent must respond with:

{
  "label": "important",
  "priority": 1
}
Allowed Labels:
spam
important
promotion
social
Priority Scale:
1 → Highest priority
5 → Lowest priority
🏆 Reward System

The reward is continuous (0.0 to 1.0) and based on:

Condition	Reward
Correct classification	+0.7
Incorrect classification	-0.3
Correct priority for important emails	+0.3

✔ Encourages correct decisions
✔ Penalizes wrong classifications
✔ Rewards partial progress

🔁 API Methods
reset()
Resets the environment
Returns first email observation
step(action)
Takes agent action
Returns:
next observation
reward
done flag
info
state()
Returns current internal state:
{
  "current_index": 2,
  "total_emails": 10
}
🧪 Tasks
🟢 Task 1 — Easy
Clear and obvious emails
Example:
"Win ₹1,00,000 now!!!" → spam
"Team meeting tomorrow" → important
🟡 Task 2 — Medium
Slightly confusing emails
Requires better understanding
Example:
"Flat 50% discount!" → promotion
"Interview scheduled" → important
🔴 Task 3 — Hard
Long or ambiguous emails
Context-based understanding required
Example:
"Suspicious login attempt detected" → important
"Weekly newsletter" → social
🧮 Grading System

Each task includes a deterministic grader:

score = correct_predictions / total_emails

Final score ranges from 0.0 to 1.0

🤖 Baseline Agent

A baseline agent uses an LLM to:

Read email content
Predict label and priority
Run baseline:
export ANTHROPIC_API_KEY=your_key
python baseline.py
🛠️ Setup Instructions
1. Clone Repository
git clone <repo-url>
cd email-triage-env
2. Install Dependencies
pip install -r requirements.txt
3. Run Environment
python app.py
🐳 Docker Setup
Build Image
docker build -t email-env .
Run Container
docker run email-env
☁️ Hugging Face Deployment
Deploy as a Docker Space
Add tag: openenv
Ensure environment runs via app.py
📊 Baseline Results
Task	Score
Easy	0.90
Medium	0.75
Hard	0.60