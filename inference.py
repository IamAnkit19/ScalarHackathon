"""
inference.py — Baseline inference for the Email Triage environment.

Phase 1: prints [START]/[STEP]/[END] structured output
Phase 2: uses OpenAI(base_url=API_BASE_URL, api_key=API_KEY) for ALL LLM calls
         so every request goes through the hackathon's LiteLLM proxy.

Environment variables (injected by hackathon validator)
-------------------------------------------------------
  API_BASE_URL   LiteLLM proxy endpoint
  API_KEY        Proxy API key
  MODEL_NAME     Model identifier
  ENV_URL        Env server URL (default: http://localhost:7860)
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request

from openai import OpenAI

# ── MUST read from injected env vars — do NOT hardcode ───────────────────────
API_BASE_URL: str = os.environ.get("API_BASE_URL", "https://router.huggingface.co/v1")
API_KEY: str      = (os.environ.get("API_KEY") or
                     os.environ.get("HF_TOKEN", ""))
MODEL_NAME: str   = os.environ.get("MODEL_NAME", "meta-llama/Llama-3.3-70B-Instruct")
ENV_URL: str      = os.environ.get("ENV_URL", "http://localhost:7860").rstrip("/")

TASK_IDS  = ["easy", "medium", "hard"]
MAX_STEPS = 5

# ── OpenAI client pointing at LiteLLM proxy (required by validator) ──────────
client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY or "dummy")


# ── HTTP helpers ──────────────────────────────────────────────────────────────

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
            print(f"  [Attempt {attempt}] {url}: {exc}", file=sys.stderr, flush=True)
            if attempt == retries:
                raise
            time.sleep(2 * attempt)
    return {}


def wait_for_server(timeout: int = 60) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        for path in ["/health", "/reset"]:
            try:
                method = "POST" if path == "/reset" else "GET"
                req = urllib.request.Request(
                    f"{ENV_URL}{path}",
                    data=(b"{}" if method == "POST" else None),
                    headers={"Content-Type": "application/json"},
                    method=method,
                )
                with urllib.request.urlopen(req, timeout=5) as r:
                    if r.status == 200:
                        print(f"Server ready at {ENV_URL}", flush=True)
                        return
            except Exception:
                pass
        time.sleep(3)
    raise RuntimeError(f"Server at {ENV_URL} not ready after {timeout}s")


# ── LLM email classifier ──────────────────────────────────────────────────────

SYSTEM_PROMPT = (
    "You are an AI email classifier. "
    "Reply with ONLY valid JSON — no markdown, no backticks, no extra text."
)

PROMPTS = {
    "easy": (
        'Classify this email as exactly one of: spam, work, personal.\n'
        'Return ONLY: {{"label":"<category>"}}\n\n'
        'Subject: {subject}\nBody: {body}'
    ),
    "medium": (
        'Classify this email and give a brief reason.\n'
        'Return ONLY: {{"label":"<spam|work|personal>","reason":"<one sentence>"}}\n\n'
        'Subject: {subject}\nBody: {body}'
    ),
    "hard": (
        'Classify this email with full triage details.\n'
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
    """Call LLM through API_BASE_URL proxy — this is the call the validator checks."""
    subject = email.get("subject", "")
    body    = email.get("body", "")
    prompt  = PROMPTS[level].format(subject=subject, body=body)

    try:
        # ← Goes through hackathon's LiteLLM proxy via API_BASE_URL + API_KEY
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

    # Get email list from server response
    emails = result.get("emails", [])

    rewards: list[float] = []
    steps_taken = 0

    for step in range(1, MAX_STEPS + 1):
        if result.get("done"):
            break

        # Get email for this step
        email = {}
        if emails and (step - 1) < len(emails):
            email = emails[step - 1]
        else:
            email = {"subject": f"Email {step}", "body": "Please review."}

        # ← LLM call through proxy
        llm_action = classify_email(email, level)

        # Build action payload for /step
        action_payload = {**llm_action, "level": level, "email_index": step - 1}

        try:
            result = http_post("/step", action_payload)
        except Exception as exc:
            print(f"  [ERROR] step {step}: {exc}", file=sys.stderr, flush=True)
            continue

        reward      = float(result.get("reward", 0.01))
        reward      = round(max(0.01, min(reward, 0.99)), 4)
        done        = result.get("done", False)
        rewards.append(reward)
        steps_taken = step

        print(f"[STEP] step={step} reward={reward:.4f} done={done}", flush=True)

        if done:
            break

    score = round(max(0.01, min(
        sum(rewards) / len(rewards) if rewards else 0.01, 0.99
    )), 4)

    print(f"[END] task={level} score={score:.4f} steps={steps_taken}", flush=True)
    return score


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("Email Triage Environment — Baseline Inference", flush=True)
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
