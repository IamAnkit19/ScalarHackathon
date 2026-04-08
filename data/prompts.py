# data/prompts.py
# Prompt templates for Easy / Medium / Hard difficulty levels

PROMPTS = {
    "easy": """You are an AI email classifier.
Classify the following email as EXACTLY ONE of: spam, work, personal.
Return ONLY valid JSON with no markdown, no extra text, no backticks.
Required format: {{"label":"<category>"}}

Subject: {subject}
Body: {body}""",

    "medium": """You are an intelligent email assistant.
Classify this email and explain briefly why.
Return ONLY valid JSON with no markdown, no extra text, no backticks.
Required format: {{"label":"<spam|work|personal>","reason":"<one concise sentence>"}}

Subject: {subject}
Body: {body}""",

    "hard": """You are an advanced email triage assistant.
Analyze and classify this email carefully.
Return ONLY valid JSON with no markdown, no extra text, no backticks.
Required format: {{
  "category":"<spam|work|personal>",
  "priority":"<low|medium|high>",
  "action":"<ignore|reply|escalate>",
  "reason":"<one concise sentence>"
}}

Subject: {subject}
Body: {body}""",
}

# Human-readable reward table shown in UI
REWARD_TABLES = {
    "easy": [
        {"action": "Correct category", "value": "+1.0", "positive": True},
        {"action": "Wrong category",   "value": "−0.2", "positive": False},
    ],
    "medium": [
        {"action": "Correct category", "value": "+0.7", "positive": True},
        {"action": "Partial match",    "value": "+0.4", "positive": True},
        {"action": "Wrong category",   "value": "−0.2", "positive": False},
    ],
    "hard": [
        {"action": "Correct category", "value": "+0.5", "positive": True},
        {"action": "Correct priority", "value": "+0.3", "positive": True},
        {"action": "Correct action",   "value": "+0.2", "positive": True},
        {"action": "Wrong category",   "value": "−0.2", "positive": False},
    ],
}
