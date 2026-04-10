"""
agents/classifier.py — Email classification via OpenAI-compatible LiteLLM proxy.

CRITICAL: Always uses OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
so every LLM call goes through the hackathon's proxy.
"""
from __future__ import annotations

import json
import os
from openai import OpenAI
from data.prompts import PROMPTS


FALLBACKS = {
    "easy":   {"label": "work"},
    "medium": {"label": "work", "reason": "fallback"},
    "hard":   {"category": "work", "priority": "medium", "action": "reply", "reason": "fallback"},
}


class EmailClassifierAgent:
    def __init__(self, api_key: str = None, base_url: str = None):
        self.api_key  = (api_key or
                         os.environ.get("API_KEY") or
                         os.environ.get("HF_TOKEN", "")).strip()
        self.base_url = (base_url or
                         os.environ.get("API_BASE_URL",
                                        "https://router.huggingface.co/v1"))
        self.model    = os.environ.get("MODEL_NAME",
                                       "meta-llama/Llama-3.3-70B-Instruct")
        # Always use OpenAI client pointing at LiteLLM proxy
        self.client   = OpenAI(base_url=self.base_url, api_key=self.api_key or "dummy")

    def classify(self, email: dict, level: str) -> dict:
        prompt = PROMPTS[level].format(
            subject=email.get("subject", ""),
            body=email.get("body", ""),
        )
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system",
                     "content": "You are an email classifier. Reply with ONLY valid JSON, no markdown."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0,
                max_tokens=256,
            )
            raw = (resp.choices[0].message.content or "{}").strip()
            return self._parse(raw, level)
        except Exception as exc:
            print(f"  [LLM error] {exc}", flush=True)
            return FALLBACKS[level]

    def _parse(self, raw: str, level: str) -> dict:
        try:
            clean = raw.strip()
            if clean.startswith("```"):
                lines = clean.splitlines()
                clean = "\n".join(lines[1:]).replace("```", "").strip()
            return json.loads(clean)
        except Exception:
            return FALLBACKS[level]
