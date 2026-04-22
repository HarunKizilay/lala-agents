"""
LLM Client — Gemini (birincil) + Claude (yedek)
Tüm ajanlar bu modülü kullanır, API anahtarı .env'den okunur.
"""
from __future__ import annotations
import os
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


def ask(prompt: str, system: str = "", temperature: float = 0.3) -> str:
    """Gemini ile sor, hata alırsa Claude'a geç."""
    try:
        return _ask_gemini(prompt, system, temperature)
    except Exception as gemini_err:
        try:
            return _ask_claude(prompt, system)
        except Exception as claude_err:
            raise RuntimeError(
                f"Her iki LLM de başarısız.\n"
                f"Gemini: {gemini_err}\n"
                f"Claude: {claude_err}"
            )


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
