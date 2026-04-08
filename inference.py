import os
import sys
from dotenv import load_dotenv
from agents.environment import EmailEnvironment
from agents.classifier import EmailClassifierAgent

def run_baseline(level: str):
    env = EmailEnvironment()
    
    key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not key or key == "your_api_key_here":
        print(f"[{level.upper()}] ERROR: ANTHROPIC_API_KEY not found in .env")
        return
        
    agent = EmailClassifierAgent(api_key=key)
    env.reset()
    
    print(f"\n▶ Running Baseline for Task Level: {level.upper()}")
    print("-" * 50)
    
    while not env.done:
        email = env.emails[env.step_idx]
        try:
            action = agent.classify(email, level)
        except Exception as e:
            action = {"label": "error", "reason": str(e)}
            
        result = env.step(action, level)
        
        correct_str = "✅ Correct" if result["info"]["step_record"]["correct"] else "❌ Wrong"
        print(f"[{env.step_idx}] Subject: {email['subject'][:30]:<30} | {correct_str}")
        
    state = env.get_state()
    print("-" * 50)
    print(f"🏁 Final Score for {level.upper()}:  Accuracy: {state['accuracy']:.2f}  |  Total Reward: {state['total_reward']}")
    print("-" * 50)

def main():
    load_dotenv()
    print("🤖 Starting Baseline OpenEnv Evaluator...")
    run_baseline("easy")
    run_baseline("medium")
    run_baseline("hard")

if __name__ == "__main__":
    main()
