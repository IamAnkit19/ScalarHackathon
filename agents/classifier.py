# agents/classifier.py
# Claude-powered email classification agent

import json
import anthropic
from data.prompts import PROMPTS


class EmailClassifierAgent:
    """
    AI Agent that classifies emails using Claude.

    Wraps the Anthropic API and handles:
      - Prompt construction
      - API call
      - JSON parsing + fallback
    """

    MODEL = "claude-sonnet-4-20250514"

    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)

    def classify(self, email: dict, level: str) -> dict:
        """
        Send email to Claude and return structured classification.

        Args:
            email:  {"subject": str, "body": str, ...}
            level:  "easy" | "medium" | "hard"

        Returns:
            Parsed JSON dict from Claude.
        """
        prompt = PROMPTS[level].format(
            subject=email["subject"],
            body=email["body"],
        )

        message = self.client.messages.create(
            model=self.MODEL,
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = message.content[0].text
        return self._parse(raw, level)

    # ── private ─────────────────────────────────────────────────────
    def _parse(self, raw: str, level: str) -> dict:
        """Parse Claude's response; return safe fallback on failure."""
        try:
            clean = raw.strip().strip("```json").strip("```").strip()
            return json.loads(clean)
        except (json.JSONDecodeError, ValueError):
            # safe fallback so episode doesn't crash
            if level == "hard":
                return {
                    "category": "work",
                    "priority": "medium",
                    "action": "reply",
                    "reason": "parse error — fallback used",
                }
            return {"label": "work", "reason": "parse error — fallback used"}
