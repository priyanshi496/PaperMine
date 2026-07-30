import asyncio
import os
from app.services.llm_service import call_llm_assistant_intent

def run():
    print("Testing intent...")
    res = call_llm_assistant_intent("hii")
    print("Result:", res)

run()
