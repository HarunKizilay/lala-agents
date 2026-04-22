"""
LLM Client — LM Studio → OpenRouter → GitHub Models → Gemini → Anthropic
Tüm ajanlar bu modülü kullanır, API anahtarları .env'den okunur.
"""
from __future__ import annotations
import os
import json
import urllib.request
from pathlib import Path
from dotenv import load_dotenv

# .env yükleme: önce LALA kökü, sonra aktif proje
for env_path in [
    Path(__file__).parent.parent / ".env",
    Path("C:/Users/aemre/Desktop/ZEKY/.env"),
]:
    if env_path.exists():
        load_dotenv(env_path)
        break

LM_STUDIO_BASE  = os.getenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1")
LM_STUDIO_MODEL = os.getenv("LM_STUDIO_MODEL",    "local-model")

OPENROUTER_MODEL    = os.getenv("OPENROUTER_DEFAULT_MODEL", "google/gemma-2-9b-it:free")
GITHUB_MODELS_MODEL = os.getenv("GITHUB_DEFAULT_MODEL",     "gpt-4o-mini")


def ask(prompt: str, system: str = "", temperature: float = 0.3) -> str:
    """1.LM Studio → 2.OpenRouter → 3.GitHub Models → 4.Gemini → 5.Anthropic"""
    errors: dict[str, str] = {}

    for name, fn in [
        ("LM Studio",     lambda: _ask_lm_studio(prompt, system, temperature)),
        ("OpenRouter",    lambda: _ask_openrouter(prompt, system, temperature)),
        ("GitHub Models", lambda: _ask_github_models(prompt, system, temperature)),
        ("Gemini",        lambda: _ask_gemini(prompt, system, temperature)),
        ("Anthropic",     lambda: _ask_claude(prompt, system)),
    ]:
        try:
            return fn()
        except Exception as e:
            errors[name] = str(e)

    detail = "\n".join(f"  {k}: {v}" for k, v in errors.items())
    raise RuntimeError(f"Tüm LLM'ler başarısız:\n{detail}")


# ── 1. LM Studio ─────────────────────────────────────────────────────────────

def _ask_lm_studio(prompt: str, system: str, temperature: float) -> str:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = json.dumps({
        "model": LM_STUDIO_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": 4096,
    }).encode()

    req = urllib.request.Request(
        f"{LM_STUDIO_BASE}/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        data = json.loads(resp.read())
    return data["choices"][0]["message"]["content"].strip()


# ── 2. OpenRouter ─────────────────────────────────────────────────────────────

def _ask_openrouter(prompt: str, system: str, temperature: float) -> str:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY bulunamadı")

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = json.dumps({
        "model": OPENROUTER_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": 4096,
    }).encode()

    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://github.com/HarunKizilay/lala-agents",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    return data["choices"][0]["message"]["content"].strip()


# ── 3. GitHub Models ──────────────────────────────────────────────────────────

def _ask_github_models(prompt: str, system: str, temperature: float) -> str:
    api_key = os.getenv("GITHUB_MODELS_TOKEN")
    if not api_key:
        raise ValueError("GITHUB_MODELS_TOKEN bulunamadı")

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = json.dumps({
        "model": GITHUB_MODELS_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": 4096,
    }).encode()

    req = urllib.request.Request(
        "https://models.inference.ai.azure.com/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    return data["choices"][0]["message"]["content"].strip()


# ── 4. Gemini ─────────────────────────────────────────────────────────────────

def _ask_gemini(prompt: str, system: str, temperature: float) -> str:
    from google import genai
    from google.genai import types

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY bulunamadı")

    model = os.getenv("GEMINI_MODEL_PRO", "gemini-2.0-flash")
    client = genai.Client(api_key=api_key)
    full_prompt = f"{system}\n\n{prompt}" if system else prompt
    response = client.models.generate_content(
        model=model,
        contents=full_prompt,
        config=types.GenerateContentConfig(temperature=temperature),
    )
    return response.text.strip()


# ── 5. Anthropic ──────────────────────────────────────────────────────────────

def _ask_claude(prompt: str, system: str) -> str:
    import anthropic

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY bulunamadı")

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=system or "Sen yardımcı bir AI asistanısın.",
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()
