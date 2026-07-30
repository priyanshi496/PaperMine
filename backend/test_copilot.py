import requests
import json
import time
import time

BASE_URL = "http://localhost:8000/api/v1"

def login():
    response = requests.post(f"{BASE_URL}/auth/login", data={
        "username": "cfo@technova.com",
        "password": "password123"
    })
    response.raise_for_status()
    return response.json()["access_token"]

QUERIES = [
    "Why did IT spending increase?",
    "Why did Cafeteria spending decrease?",
    "Should we continue working with Dell?",
    "Should we continue working with Metro?",
    "Why was invoice OBH-2026-9999 rejected?",
    "Give me today's executive summary."
]

def chat(token, query, history):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "query": query,
        "chat_history": history
    }
    
    response = requests.post(f"{BASE_URL}/assistant/chat", json=payload, headers=headers, stream=True)
    
    full_text = ""
    sources = []
    
    for line in response.iter_lines():
        if line:
            line = line.decode('utf-8')
            if line.startswith("data: "):
                data_str = line[6:].strip()
                if not data_str:
                    continue
                try:
                    data = json.loads(data_str)
                    if "sources" in data:
                        sources = data["sources"]
                    if "chunk" in data:
                        full_text += data["chunk"]
                except Exception as e:
                    pass
                    
    return full_text, sources

def main():
    print("Logging in as CFO...")
    token = login()
    print("Login successful!\n")
    
    history = []
    
    for q in QUERIES:
        print(f"=====================================")
        print(f"QUERY: {q}")
        print(f"=====================================")
        
        start_time = time.time()
        answer, sources = chat(token, q, history)
        elapsed = time.time() - start_time
        
        print(f"TIME: {elapsed:.2f}s")
        if sources:
            print(f"SOURCES: {len(sources)}")
        print(f"ANSWER:\n{answer}\n")
        
        history.append({"role": "user", "content": q})
        history.append({"role": "assistant", "content": answer})

if __name__ == "__main__":
    main()
