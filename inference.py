import os
import requests
from dotenv import load_dotenv

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:7860")
MODEL_NAME = os.getenv("MODEL_NAME", "baseline-model")

MAX_STEPS = 5
SUCCESS_SCORE_THRESHOLD = 0.5


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


def run_task(level):
    rewards = []
    steps_taken = 0

    log_start(task=level)

    # reset
    res = requests.post(f"{BASE_URL}/reset")
    result = res.json()

    for step in range(1, MAX_STEPS + 1):
        if result.get("done"):
            break

        action = {"level": level, "email_index": step - 1}

        res = requests.post(f"{BASE_URL}/step", json=action)
        result = res.json()

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


def main():
    load_dotenv()
    run_task("easy")
    run_task("medium")
    run_task("hard")


if __name__ == "__main__":
    main()