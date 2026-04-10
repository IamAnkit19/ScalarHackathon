"""
inference.py — Baseline inference for the Email Classifier environment.

IMPORTANT: Uses the OpenAI client with the injected API_BASE_URL and API_KEY
so all LLM calls go through the hackathon's LiteLLM proxy.

Environment variables
---------------------
  API_BASE_URL  LiteLLM proxy endpoint  (injected by hackathon)
  API_KEY       Proxy API key           (injected by hackathon)
  HF_TOKEN      Fallback API key
  MODEL_NAME    Model to use
  ENV_URL       Env server URL (default: http://localhost:7860)
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request

from openai import OpenAI

# ── Config — MUST use injected env vars for LLM calls ────────────────────────
API_BASE_URL: str = os.environ.get("API_BASE_URL", "https://router.huggingface.co/v1")
API_KEY: str      = os.environ.get("API_KEY") or os.environ.get("HF_TOKEN", "")
MODEL_NAME: str   = os.environ.get("MODEL_NAME", "meta-llama/Llama-3.3-70B-Instruct")
ENV_URL: str      = os.environ.get("ENV_URL", "http://localhost:7860").rstrip("/")

MAX_STEPS   = 5
TASK_IDS    = ["easy", "medium", "hard"]

# ── OpenAI client — always use API_BASE_URL + API_KEY (LiteLLM proxy) ────────
client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)


# ── HTTP helpers (stdlib only) ────────────────────────────────────────────────

def http_post(path: str, body: dict = None, retries: int = 3) -> dict:
    url  = f"{ENV_URL}{path}"
    data = json.dumps(body or {}).encode()
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(
                url, data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as exc:
            print(f"  [HTTP {exc.code}] {url}", file=sys.stderr, flush=True)
            if attempt == retries:
                raise
        except Exception as exc:
            print(f"  [Attempt {attempt}] {url} failed: {exc}", file=sys.stderr, flush=True)
            if attempt == retries:
                raise
            time.sleep(2 * attempt)
    return {}


def wait_for_server(timeout: int = 60) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{ENV_URL}/health", timeout=5) as r:
                if r.status == 200:
                    print(f"Server ready at {ENV_URL}", flush=True)
                    return
        except Exception:
            pass
        # also try /reset as health proxy
        try:
            req = urllib.request.Request(
                f"{ENV_URL}/reset", data=b"{}",
                headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=5) as r:
                if r.status == 200:
                    print(f"Server ready at {ENV_URL}", flush=True)
                    return
        except Exception:
            pass
        time.sleep(3)
    raise RuntimeError(f"Server at {ENV_URL} not ready after {timeout}s")


# ── LLM email classifier — calls through LiteLLM proxy ───────────────────────

SYSTEM_PROMPT = (
    "You are an AI email classifier. Classify the email and reply with ONLY "
    "valid JSON — no markdown, no backticks, no extra text."
)

PROMPTS = {
    "easy": (
        'Classify as EXACTLY ONE of: spam, work, personal.\n'
        'Return ONLY: {{"label":"<category>"}}\n\n'
        'Subject: {subject}\nBody: {body}'
    ),
    "medium": (
        'Classify the email and explain briefly.\n'
        'Return ONLY: {{"label":"<spam|work|personal>","reason":"<one sentence>"}}\n\n'
        'Subject: {subject}\nBody: {body}'
    ),
    "hard": (
        'Analyse and classify this email carefully.\n'
        'Return ONLY:\n'
        '{{"category":"<spam|work|personal>","priority":"<low|medium|high>",'
        '"action":"<ignore|reply|escalate>","reason":"<one sentence>"}}\n\n'
        'Subject: {subject}\nBody: {body}'
    ),
}

FALLBACKS = {
    "easy":   {"label": "work"},
    "medium": {"label": "work", "reason": "fallback"},
    "hard":   {"category": "work", "priority": "medium", "action": "reply", "reason": "fallback"},
}


def classify_email(email: dict, level: str) -> dict:
    """Call LLM through API_BASE_URL proxy to classify one email."""
    subject = email.get("subject", "")
    body    = email.get("body", "")
    prompt  = PROMPTS[level].format(subject=subject, body=body)

    try:
        # ← THIS is the call that goes through the hackathon's LiteLLM proxy
        resp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": prompt},
            ],
            temperature=0.0,
            max_tokens=200,
        )
        raw = (resp.choices[0].message.content or "{}").strip()
        # strip markdown fences if model adds them
        if raw.startswith("```"):
            lines = raw.splitlines()
            raw = "\n".join(lines[1:]).replace("```", "").strip()
        return json.loads(raw)
    except Exception as exc:
        print(f"  [LLM error] {exc}", file=sys.stderr, flush=True)
        return FALLBACKS[level]


# ── Task runner ───────────────────────────────────────────────────────────────

def run_task(level: str) -> float:
    print(f"[START] task={level}", flush=True)

    try:
        result = http_post("/reset")
    except Exception as exc:
        print(f"[END] task={level} score=0.01 steps=0", flush=True)
        print(f"  [ERROR] reset failed: {exc}", file=sys.stderr, flush=True)
        return 0.01

    rewards:     list[float] = []
    steps_taken: int         = 0

    # Pull email list from observation if present
    obs    = result.get("observation", result)
    emails = obs.get("emails", []) if isinstance(obs, dict) else []

    for step in range(1, MAX_STEPS + 1):
        if result.get("done"):
            break

        # Get the email for this step from observation or use index
        email = {}
        if emails and step - 1 < len(emails):
            email = emails[step - 1]
        else:
            email = {"subject": f"Email {step}", "body": "Please review this email."}

        # ← LLM call through proxy
        action = classify_email(email, level)
        action["level"]       = level
        action["email_index"] = step - 1

        try:
            result = http_post("/step", action)
        except Exception as exc:
            print(f"  [ERROR] step {step} failed: {exc}", file=sys.stderr, flush=True)
            continue

        reward = float(result.get("reward", 0.01))
        reward = round(max(0.01, min(reward, 0.99)), 4)
        done   = result.get("done", False)

        rewards.append(reward)
        steps_taken = step

        print(f"[STEP] step={step} reward={reward:.4f} done={done}", flush=True)

        if done:
            break

    score   = round(max(0.01, min(sum(rewards) / len(rewards), 0.99)), 4) if rewards else 0.01
    success = score >= 0.50

    print(f"[END] task={level} score={score:.4f} steps={steps_taken}", flush=True)
    return score


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("Email Classifier Agent — Baseline Inference", flush=True)
    print(f"Model:    {MODEL_NAME}", flush=True)
    print(f"Base URL: {API_BASE_URL}", flush=True)
    print(f"Env URL:  {ENV_URL}", flush=True)

    if not API_KEY:
        print("[ERROR] API_KEY / HF_TOKEN not set.", flush=True)
        sys.exit(1)

    try:
        wait_for_server(timeout=60)
    except RuntimeError as exc:
        print(f"[ERROR] {exc}", flush=True)
        sys.exit(1)

    scores: dict[str, float] = {}
    t0 = time.time()

    for level in TASK_IDS:
        try:
            scores[level] = run_task(level)
        except Exception as exc:
            import traceback
            print(f"[END] task={level} score=0.01 steps=0", flush=True)
            print(f"  [ERROR] {level} crashed: {exc}", file=sys.stderr, flush=True)
            traceback.print_exc(file=sys.stderr)
            scores[level] = 0.01

    avg = sum(scores.values()) / len(scores)
    print(f"\nAverage score: {avg:.4f} | Runtime: {time.time()-t0:.1f}s", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        import traceback
        print(f"[FATAL] {exc}", flush=True)
        traceback.print_exc()
        sys.exit(1)
