# utils/reward.py
# Reward calculation logic — core RL concept


def calculate_reward(email: dict, result: dict, level: str) -> dict:
    """
    Calculate reward for agent's action.

    Returns:
        {
          "reward": float,
          "correct": bool,
          "breakdown": dict   # only used in hard level
        }
    """
    if level == "easy":
        correct = result.get("label", "") == email["label"]
        return {
            "reward": round(1.0 if correct else -0.2, 2),
            "correct": correct,
            "breakdown": {},
        }

    if level == "medium":
        correct = result.get("label", "") == email["label"]
        return {
            "reward": round(0.7 if correct else -0.2, 2),
            "correct": correct,
            "breakdown": {},
        }

    # hard level — granular reward
    cat_ok = result.get("category", "") == email["label"]
    pri_ok = result.get("priority", "") == email["priority"]
    act_ok = result.get("action",   "") == email["action"]

    if not cat_ok:
        reward = -0.2
    else:
        reward = 0.5 + (0.3 if pri_ok else 0) + (0.2 if act_ok else 0)

    return {
        "reward": round(reward, 2),
        "correct": cat_ok,
        "breakdown": {
            "category": cat_ok,
            "priority": pri_ok,
            "action":   act_ok,
        },
    }
