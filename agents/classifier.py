"""
agents/classifier.py — Email classification agent.
Uses the OpenAI client pointed at API_BASE_URL (LiteLLM proxy).
"""
from __future__ import annotations

import json
import os

from openai import OpenAI

from data.prompts import PROMPTS


class EmailClassifierAgent:
    """
    AI agent that classifies emails using the LiteLLM proxy.
    Initialised with the injected API_BASE_URL and API_KEY.
    """

    def __init__(self, api_key: str = None, base_url: str = None):
        self.base_url = base_url or os.environ.get("API_BASE_URL", "https://router.huggingface.co/v1")
        self.api_key  = api_key  or os.environ.get("API_KEY") or os.environ.get("HF_TOKEN", "")
        self.model    = os.environ.get("MODEL_NAME", "meta-llama/Llama-3.3-70B-Instruct")

        # ← Always use OpenAI client pointed at LiteLLM proxy
        self.client = OpenAI(base_url=self.base_url, api_key=self.api_key)

    def classify(self, email: dict, level: str) -> dict:
        prompt = PROMPTS[level].format(
            subject=email.get("subject", ""),
            body=email.get("body", ""),
        )
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an AI email classifier. Reply with ONLY valid JSON."},
                    {"role": "user",   "content": prompt},
                ],
                temperature=0.0,
                max_tokens=300,
            )
            raw = (resp.choices[0].message.content or "{}").strip()
            return self._parse(raw, level)
        except Exception as exc:
            print(f"  [LLM error] {exc}")
            return self._fallback(level)

    def _parse(self, raw: str, level: str) -> dict:
        try:
            clean = raw.strip()
            if clean.startswith("```"):
                lines = clean.splitlines()
                clean = "\n".join(lines[1:]).replace("```", "").strip()
            return json.loads(clean)
        except (json.JSONDecodeError, ValueError):
            return self._fallback(level)

    def _fallback(self, level: str) -> dict:
        if level == "hard":
            return {"category": "work", "priority": "medium", "action": "reply", "reason": "fallback"}
        return {"label": "work", "reason": "fallback"}
