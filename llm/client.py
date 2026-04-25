"""
LLM Client — NVIDIA NIM → LM Studio → OpenRouter → GitHub Models → Gemini → Anthropic
Tüm ajanlar bu modülü kullanır, API anahtarları .env'den okunur.
"""
from __future__ import annotations
import os
import json
import urllib.request
import concurrent.futures
from pathlib import Path
from dotenv import load_dotenv

_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=4)

def _with_timeout(fn, seconds: int):
    fut = _EXECUTOR.submit(fn)
    return fut.result(timeout=seconds)

# .env yükleme: önce LALA kökü, sonra aktif proje
for env_path in [
    Path(__file__).parent.parent / ".env",
    Path("C:/Users/aemre/Desktop/ZEKY/.env"),
    Path("/root/LALA/.env"),
]:
    if env_path.exists():
        load_dotenv(env_path)
        break

# ── Provider ayarları ─────────────────────────────────────────────────────────

NVIDIA_BASE  = "https://integrate.api.nvidia.com/v1"
NVIDIA_MODEL = os.getenv("NVIDIA_MODEL", "meta/llama-3.3-70b-instruct")

LM_STUDIO_BASE  = os.getenv("LM_STUDIO_BASE_URL", "http://100.109.228.17:1234/v1")
LM_STUDIO_MODEL = os.getenv("LM_STUDIO_MODEL",    "google/gemma-4-e4b")

OPENROUTER_MODEL    = os.getenv("OPENROUTER_DEFAULT_MODEL", "google/gemma-4-31b-it:free")
GITHUB_MODELS_MODEL = os.getenv("GITHUB_DEFAULT_MODEL",     "gpt-4o-mini")


def ask(prompt: str, system: str = "", temperature: float = 0.3) -> str:
    """1.NVIDIA NIM → 2.LM Studio → 3.OpenRouter → 4.GitHub Models → 5.Gemini → 6.Anthropic"""
    errors: dict[str, str] = {}

    for name, fn in [
        ("NVIDIA NIM",    lambda: _ask_nvidia(prompt, system, temperature)),
        ("LM Studio",     lambda: _ask_lm_studio(prompt, system, temperature)),
        ("OpenRouter",    lambda: _ask_openrouter(prompt, system, temperature)),
        ("GitHub Models", lambda: _ask_github_models(prompt, system, temperature)),
        ("Gemini",        lambda: _ask_gemini(prompt, system, temperature)),
        ("Anthropic",     lambda: _ask_claude(prompt, system)),
    ]:
        try:
            result = fn()
            if name != "NVIDIA NIM":
                import logging
                logging.getLogger(__name__).warning("NVIDIA atlandı, kullanılan: %s", name)
            return result
        except Exception as e:
            errors[name] = str(e)

    detail = "\n".join(f"  {k}: {v}" for k, v in errors.items())
    raise RuntimeError(f"Tüm LLM'ler başarısız:\n{detail}")


def ask_fast(prompt: str, system: str = "", temperature: float = 0.3) -> str:
    """Hızlı/kısa görevler için — sadece NVIDIA veya LM Studio."""
    for name, fn in [
        ("NVIDIA NIM", lambda: _ask_nvidia(prompt, system, temperature)),
        ("LM Studio",  lambda: _ask_lm_studio(prompt, system, temperature)),
    ]:
        try:
            return fn()
        except Exception:
            pass
    return ask(prompt, system, temperature)


# ── 1. NVIDIA NIM ─────────────────────────────────────────────────────────────

def _ask_nvidia(prompt: str, system: str, temperature: float,
                model: str = "") -> str:
    api_key = os.getenv("NVIDIA_API_KEY")
    if not api_key:
        raise ValueError("NVIDIA_API_KEY bulunamadı")

    mdl = model or NVIDIA_MODEL
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = json.dumps({
        "model": mdl,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": 8192,
        "stream": False,
    }).encode()

    req = urllib.request.Request(
        f"{NVIDIA_BASE}/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())
    return data["choices"][0]["message"]["content"].strip()


# ── 2. LM Studio ─────────────────────────────────────────────────────────────

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
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())
    return data["choices"][0]["message"]["content"].strip()


# ── 3. OpenRouter ─────────────────────────────────────────────────────────────

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
    with urllib.request.urlopen(req, timeout=90) as resp:
        data = json.loads(resp.read())
    return data["choices"][0]["message"]["content"].strip()


# ── 4. GitHub Models ──────────────────────────────────────────────────────────

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
    with urllib.request.urlopen(req, timeout=90) as resp:
        data = json.loads(resp.read())
    return data["choices"][0]["message"]["content"].strip()


# ── 5. Gemini ─────────────────────────────────────────────────────────────────

def _ask_gemini(prompt: str, system: str, temperature: float) -> str:
    from google import genai
    from google.genai import types

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY bulunamadı")

    model = os.getenv("GEMINI_MODEL_FLASH", "gemini-2.0-flash")
    client = genai.Client(api_key=api_key)
    full_prompt = f"{system}\n\n{prompt}" if system else prompt
    def _call():
        return client.models.generate_content(
            model=model,
            contents=full_prompt,
            config=types.GenerateContentConfig(temperature=temperature),
        ).text.strip()
    return _with_timeout(_call, 90)


# ── 6. Anthropic ──────────────────────────────────────────────────────────────

def _ask_claude(prompt: str, system: str) -> str:
    import anthropic

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY bulunamadı")

    client = anthropic.Anthropic(api_key=api_key)
    def _call():
        return client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=system or "Sen yardımcı bir AI asistanısın.",
            messages=[{"role": "user", "content": prompt}],
        ).content[0].text.strip()
    return _with_timeout(_call, 90)
