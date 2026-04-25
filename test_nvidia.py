"""
NVIDIA NIM bağlantı testi — çalıştır: python test_nvidia.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from llm.client import _ask_nvidia

def test_nvidia():
    print("NVIDIA NIM test ediliyor...")
    try:
        result = _ask_nvidia(
            prompt="Merhaba! Türkçe olarak kendini tanıt, 2 cümle yeterli.",
            system="Sen yardımcı bir AI asistanısın.",
            temperature=0.3,
        )
        print(f"\n✅ NVIDIA NIM ÇALIŞIYOR\nModel yanıtı:\n{result}\n")
        return True
    except Exception as e:
        print(f"\n❌ NVIDIA NIM HATA: {e}\n")
        return False

def test_full_chain():
    print("Tam zincir test ediliyor (NVIDIA → LM Studio → ... → Anthropic)...")
    from llm.client import ask
    try:
        result = ask("Merhaba, 1 cümleyle kendini tanıt.")
        print(f"\n✅ ZİNCİR ÇALIŞIYOR\nYanıt: {result}\n")
    except Exception as e:
        print(f"\n❌ ZİNCİR HATA: {e}\n")

if __name__ == "__main__":
    ok = test_nvidia()
    if ok:
        test_full_chain()
    else:
        print("İpucu: .env dosyasına NVIDIA_API_KEY eklediğinden emin ol")
        print("       https://build.nvidia.com → API Keys")
