# agents/environment.py
# State-based RL environment for email classification

from data.emails  import EMAILS
from utils.reward import calculate_reward


class EmailEnvironment:
    """
    Simulates a Reinforcement Learning environment.

    Lifecycle:
        reset() → step(action) × N → done = True
    """

    def __init__(self):
        self.emails: list  = EMAILS
        self.step_idx: int = 0
        self.done: bool    = False
        self.total_reward: float = 0.0
        self.correct: int  = 0
        self.history: list = []          # list of step results
        self.cat_counts: dict = {"spam": 0, "work": 0, "personal": 0}

    # ── public API ──────────────────────────────────────────────────
    def reset(self) -> dict:
        """Reset environment to initial state. Returns first observation."""
        self.step_idx    = 0
        self.done        = False
        self.total_reward = 0.0
        self.correct     = 0
        self.history     = []
        self.cat_counts  = {"spam": 0, "work": 0, "personal": 0}
        return self._observation()

    def step(self, action: dict, level: str) -> dict:
        """
        Process one agent action.

        Args:
            action: dict returned by Claude (e.g. {"label": "spam"})
            level:  "easy" | "medium" | "hard"

        Returns:
            {
              "observation": dict | None,
              "reward":      float,
              "done":        bool,
              "info":        dict
            }
        """
        if self.done:
            raise RuntimeError("Episode is finished. Call reset() first.")

        email  = self.emails[self.step_idx]
        result = calculate_reward(email, action, level)

        # update state
        self.total_reward = round(self.total_reward + result["reward"], 2)
        if result["correct"]:
            self.correct += 1

        predicted_cat = action.get("category" if level == "hard" else "label", "unknown")
        if predicted_cat in self.cat_counts:
            self.cat_counts[predicted_cat] += 1

        step_record = {
            "step":    self.step_idx + 1,
            "email":   email,
            "action":  action,
            "reward":  result["reward"],
            "correct": result["correct"],
            "breakdown": result.get("breakdown", {}),
        }
        self.history.append(step_record)
        self.step_idx += 1

        if self.step_idx >= len(self.emails):
            self.done = True

        return {
            "observation": None if self.done else self._observation(),
            "reward":      result["reward"],
            "done":        self.done,
            "info": {
                "total_reward": self.total_reward,
                "correct":      self.correct,
                "accuracy":     round(self.correct / self.step_idx, 3),
                "cat_counts":   self.cat_counts,
                "step_record":  step_record,
            },
        }

    def get_state(self) -> dict:
        """Return full current environment state (used by Flask API)."""
        return {
            "step":         self.step_idx,
            "total":        len(self.emails),
            "done":         self.done,
            "total_reward": self.total_reward,
            "correct":      self.correct,
            "accuracy":     round(self.correct / self.step_idx, 3) if self.step_idx else 0,
            "cat_counts":   self.cat_counts,
            "history":      self.history,
        }

    # ── private ─────────────────────────────────────────────────────
    def _observation(self) -> dict:
        """Current email as observation."""
        if self.step_idx >= len(self.emails):
            return {}
        e = self.emails[self.step_idx]
        return {
            "id":      e["id"],
            "sender":  e["sender"],
            "subject": e["subject"],
            "body":    e["body"],
        }
