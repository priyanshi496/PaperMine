"""
ollama_client.py
─────────────────────────────────────────────────────
Thin, self-contained client for the local Ollama server.

Env vars (set in .env):
    OLLAMA_HOST   → defaults to http://localhost:11434
    OLLAMA_MODEL  → defaults to qwen3:8b

Usage:
    from app.services.ollama_client import ollama_chat, ollama_generate
"""

import os
import json
import urllib.request
import urllib.error
from typing import Optional


def _get_ollama_host() -> str:
    return os.environ.get("OLLAMA_HOST", "http://localhost:11434")

def _get_ollama_model() -> str:
    return os.environ.get("OLLAMA_MODEL", "qwen3:8b")


def _post(endpoint: str, payload: dict, timeout: int = 120) -> Optional[dict]:
    host = _get_ollama_host()
    url = f"{host}{endpoint}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = response.read().decode("utf-8")
            return json.loads(body)
    except urllib.error.URLError as e:
        print(f"[OllamaClient] Connection error -> {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"[OllamaClient] JSON decode error -> {e}")
        return None
    except Exception as e:
        print(f"[OllamaClient] Unexpected error -> {e}")
        return None


def ollama_chat(
    messages: list,
    model: Optional[str] = None,
    system: Optional[str] = None,
    temperature: float = 0.3,
) -> Optional[str]:
    """Multi-turn chat via /api/chat."""
    model = model or _get_ollama_model()
    full_messages = []
    if system:
        full_messages.append({"role": "system", "content": system})
    full_messages.extend(messages)

    payload = {
        "model": model,
        "messages": full_messages,
        "stream": False,
        "options": {"temperature": temperature},
    }
    result = _post("/api/chat", payload)
    if result and "message" in result:
        return result["message"]["content"].strip()
    return None


def ollama_generate(
    prompt: str,
    model: Optional[str] = None,
    system: Optional[str] = None,
    temperature: float = 0.3,
) -> Optional[str]:
    """Single-shot generation via /api/generate."""
    model = model or _get_ollama_model()
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature},
    }
    if system:
        payload["system"] = system
    result = _post("/api/generate", payload)
    if result and "response" in result:
        return result["response"].strip()
    return None


def ollama_is_available() -> bool:
    """Quick health-check. Returns True if Ollama is reachable."""
    host = _get_ollama_host()
    try:
        with urllib.request.urlopen(f"{host}/api/tags", timeout=3) as r:
            return r.status == 200
    except Exception:
        return False
