import os
import requests
try:
    from openai import OpenAI
except ImportError:
    print("[START]", flush=True)
    print("task=error", flush=True)
    print("env=error", flush=True)
    print("model=error", flush=True)
    print("[END]", flush=True)
    print("success=False", flush=True)
    print("steps=0", flush=True)
    print("score=0.0", flush=True)
    print("rewards=[]", flush=True)
    exit(0)

# ✅ LLM Proxy Config (MANDATORY)
API_BASE_URL = os.environ["API_BASE_URL"]
API_KEY = os.environ["API_KEY"]
MODEL_NAME = os.environ["MODEL_NAME"]

# ✅ Your Environment API
ENV_URL = "http://localhost:7860"

MAX_STEPS = 5
SUCCESS_SCORE_THRESHOLD = 0.5


# ---------- LOGGING ----------
def log_start(task):
    print("[START]", flush=True)
    print(f"task={task}", flush=True)
    print("env=email_env", flush=True)
    print(f"model={MODEL_NAME}", flush=True)


def log_step(step, action, reward, done):
    print("[STEP]", flush=True)
    print(f"step={step}", flush=True)
    print(f"action={action}", flush=True)
    print(f"reward={reward}", flush=True)
    print(f"done={done}", flush=True)


def log_end(success, steps, score, rewards):
    print("[END]", flush=True)
    print(f"success={success}", flush=True)
    print(f"steps={steps}", flush=True)
    print(f"score={score}", flush=True)
    print(f"rewards={rewards}", flush=True)


# ---------- LLM CALL ----------
def get_llm_label(client, email_text):
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "Classify email into spam, urgent, or normal."},
                {"role": "user", "content": email_text}
            ],
        )
        return response.choices[0].message.content.strip().lower()
    except Exception:
        return "normal"  # fallback


# ---------- TASK RUNNER ----------
def run_task(level):
    rewards = []
    steps_taken = 0

    log_start(task=level)

    # ✅ Initialize LLM client
    client = OpenAI(
        base_url=API_BASE_URL,
        api_key=API_KEY
    )

    # reset env
    try:
        res = requests.post(f"{ENV_URL}/reset")
        result = res.json()
    except Exception:
        log_end(False, 0, 0.0, [])
        return

    for step in range(1, MAX_STEPS + 1):
        if result.get("done"):
            break

        # get email text safely
        email_text = result.get("observation", {}).get("email_text", "test email")

        # ✅ REQUIRED: LLM CALL (this fixes your error)
        label = get_llm_label(client, email_text)

        action = {
            "level": level,
            "email_index": step - 1,
            "label": label
        }

        # send to environment
        try:
            res = requests.post(f"{ENV_URL}/step", json=action)
            result = res.json()
        except Exception:
            reward = 0.0
            done = True
            log_step(step, action, reward, done)
            break

        reward = result.get("reward", 0.0)
        done = result.get("done", False)

        rewards.append(reward)
        steps_taken = step

        log_step(step, action, reward, done)

        if done:
            break

    score = sum(rewards) / len(rewards) if rewards else 0.0
    success = score >= SUCCESS_SCORE_THRESHOLD

    log_end(success, steps_taken, score, rewards)


# ---------- MAIN ----------
def main():
    run_task("easy")
    run_task("medium")
    run_task("hard")


if __name__ == "__main__":
    main()