"""
CHIKU PRO - LLM Router
Routes prompts to OpenAI (cloud) or Ollama (local) with graceful fallback.
"""

import os
import requests

# ─── Try importing OpenAI ────────────────────────────────────────────────────
_openai_available = False
try:
    from openai import OpenAI
    _openai_available = True
except ImportError:
    _openai_available = False


def call_openai(prompt, system_prompt=None):
    """Call OpenAI GPT API. Returns response text or None."""
    if not _openai_available:
        return None

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None

    try:
        client = OpenAI(api_key=api_key)

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        else:
            messages.append({"role": "system", "content": "You convert commands into structured JSON."})

        messages.append({"role": "user", "content": prompt})

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0,
            max_tokens=500,
        )

        return response.choices[0].message.content

    except Exception:
        return None


def call_ollama(prompt, system_prompt=None):
    """Call local Ollama API. Returns response text or None."""
    try:
        payload = {
            "model": "mistral",
            "prompt": prompt,
            "stream": False,
        }

        if system_prompt:
            payload["system"] = system_prompt

        response = requests.post(
            "http://localhost:11434/api/generate",
            json=payload,
            timeout=30,
        )

        if response.status_code == 200:
            return response.json().get("response")
        return None

    except (requests.ConnectionError, requests.Timeout):
        return None
    except Exception:
        return None


def call_gemini(prompt, system_prompt=None):
    """Call Google Gemini API. Returns response text or None."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None

    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"

        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\nUser: {prompt}"

        payload = {
            "contents": [{"parts": [{"text": full_prompt}]}],
            "generationConfig": {
                "temperature": 0,
                "maxOutputTokens": 500,
            }
        }

        response = requests.post(url, json=payload, timeout=30)

        if response.status_code == 200:
            data = response.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
        return None

    except Exception:
        return None


def get_llm_response(prompt, system_prompt=None):
    """
    Get LLM response with fallback chain:
    1. OpenAI (cloud, if API key set)
    2. Gemini (cloud, if API key set)  
    3. Ollama (local, if running)
    Returns response text or None if all fail.
    """
    # Try OpenAI first
    result = call_openai(prompt, system_prompt)
    if result:
        return result

    # Try Gemini
    result = call_gemini(prompt, system_prompt)
    if result:
        return result

    # Try Ollama (local)
    result = call_ollama(prompt, system_prompt)
    if result:
        return result

    return None