"""
NVIDIA NIM baglantiyi test eder — calistir: python test_nvidia.py
Birden fazla modeli dener, hangisi calisiyorsa goruntüler.
"""
import sys, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

# Windows konsol unicode hatasi önlemi
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf-8-sig"):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

import json, urllib.request

NVIDIA_BASE = "https://integrate.api.nvidia.com/v1"

# Test edilecek modeller — en üstteki önce denenir
CANDIDATE_MODELS = [
    ("meta/llama-3.1-8b-instruct",          "Meta Llama 3.1 8B (stabil, hizli)"),
    ("meta/llama-3.3-70b-instruct",          "Meta Llama 3.3 70B"),
    ("nvidia/llama-3.1-nemotron-70b-instruct","Nemotron 70B"),
    ("deepseek-ai/deepseek-v4-flash",        "DeepSeek V4 Flash (yeni)"),
]

def ask_nvidia(prompt: str, model: str, timeout: int = 30) -> str:
    api_key = os.getenv("NVIDIA_API_KEY")
    if not api_key:
        raise ValueError("NVIDIA_API_KEY bulunamadi")

    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 100,
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
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read())
    return data["choices"][0]["message"]["content"].strip()


def list_available_models() -> list:
    """NVIDIA'nin mevcut modellerini listele."""
    api_key = os.getenv("NVIDIA_API_KEY")
    if not api_key:
        return []
    try:
        req = urllib.request.Request(
            f"{NVIDIA_BASE}/models",
            headers={"Authorization": f"Bearer {api_key}"},
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        return [m["id"] for m in data.get("data", [])]
    except Exception as e:
        print(f"  Model listesi alinamadi: {e}")
        return []


if __name__ == "__main__":
    print("=" * 55)
    print("NVIDIA NIM Baglanti Testi")
    print("=" * 55)

    # Mevcut modelleri listele
    print("\n[1] Kullanilabilir modeller listeleniyor...")
    models = list_available_models()
    if models:
        print(f"  {len(models)} model bulundu. Ilk 10:")
        for m in models[:10]:
            print(f"    - {m}")
    else:
        print("  (Liste alinamadi, model testine geciliyor)")

    # Her modeli sirayla dene
    working_model = None
    print("\n[2] Model testleri:")
    for model_id, desc in CANDIDATE_MODELS:
        print(f"\n  Deneniyor: {model_id}")
        print(f"  ({desc})")
        try:
            result = ask_nvidia("Merhaba! 1 cumlede kendini tanitir misin?", model_id, timeout=25)
            print(f"  BASARILI! Yanit:\n    {result[:200]}")
            working_model = model_id
            break
        except Exception as e:
            print(f"  BASARISIZ: {e}")

    print("\n" + "=" * 55)
    if working_model:
        print(f"SONUC: NVIDIA NIM calisiyor!")
        print(f"Calisilan model: {working_model}")
        print(f"\n.env dosyasina ekle:")
        print(f"  NVIDIA_MODEL={working_model}")
    else:
        print("SONUC: Hicbir model calismiyor.")
        print("API key dogru mu? build.nvidia.com -> API Keys")
    print("=" * 55)
