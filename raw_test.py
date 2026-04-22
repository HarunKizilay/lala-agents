"""Ham API ile long-polling testi — framework yok."""
import urllib.request, urllib.parse, json, ssl, os, time
from dotenv import load_dotenv
from pathlib import Path

for p in [Path(__file__).parent / ".env", Path("C:/Users/aemre/Desktop/ZEKY/.env")]:
    if p.exists():
        load_dotenv(p); break

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ctx = ssl._create_unverified_context()

def api(method, params=None):
    url = f"https://api.telegram.org/bot{TOKEN}/{method}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, context=ctx, timeout=35) as r:
        return json.loads(r.read())

# Bot bilgisi
me = api("getMe")
print(f"Bot: @{me['result']['username']}")

# Webhook sil
api("deleteWebhook", {"drop_pending_updates": "false"})
print("Webhook silindi. Mesaj bekleniyor... (Ctrl+C ile dur)")

offset = 0
while True:
    try:
        data = api("getUpdates", {"offset": offset, "timeout": 20, "limit": 10})
        updates = data.get("result", [])
        if updates:
            for u in updates:
                offset = u["update_id"] + 1
                msg = u.get("message", {})
                chat_id = msg.get("chat", {}).get("id")
                text = msg.get("text", "")
                print(f"UPDATE! chat_id={chat_id} text={text!r}")
                # Cevap gönder
                api("sendMessage", {"chat_id": chat_id, "text": f"Aldım: {text}"})
                print(f"Cevap gönderildi -> {chat_id}")
        else:
            print(".", end="", flush=True)
    except KeyboardInterrupt:
        print("\nDurduruluyor.")
        break
    except Exception as e:
        print(f"\nHata: {e}")
        time.sleep(2)
