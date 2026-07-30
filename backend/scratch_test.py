import os
import sys
from app.db.database import SessionLocal
from app.services.assistant import run_assistant_query

def test():
    db = SessionLocal()
    history = []
    
    queries = [
        "Summarize invoice OBH-2026-0002",
        "What items were purchased?",
        "What is the total spent on this invoice?",
        "Who issued it?",
        "When is it due?",
        "how much have I spent on coffee"
    ]
    
    for q in queries:
        print(f"\n--- Q: {q} ---")
        res = run_assistant_query(db, q, chat_history=history)
        ans = res.get("answer")
        print(f"A: {ans}")
        history.append({"role": "user", "content": q})
        history.append({"role": "assistant", "content": ans})

if __name__ == "__main__":
    test()
