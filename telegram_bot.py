"""
LALA Telegram Bot — Ham HTTP, framework yok.
Komutlar:
  /durum              — Bot durumu
  /dev <görev>        — Dev ajanı
  /dev <görev> --apply --push
  /qa <görev>         — QA ajanı
  /security           — Güvenlik taraması
  /doc <görev>        — Dokümantasyon
  /debug <görev>      — Debug
  /master <görev>     — Master ajan
  /iptal              — Bekleyen işlemi iptal et
"""
from __future__ import annotations
import asyncio, json, logging, os, ssl, sys, io, urllib.request, urllib.parse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

# UTF-8 stdout
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from dotenv import load_dotenv
for p in [Path(__file__).parent / ".env", Path("C:/Users/aemre/Desktop/ZEKY/.env")]:
    if p.exists():
        load_dotenv(p); break

logging.basicConfig(format="%(asctime)s [%(levelname)s] %(message)s", level=logging.INFO)
log = logging.getLogger(__name__)

TOKEN      = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_ID = int(os.getenv("TELEGRAM_CHAT_ID", "0"))
DEFAULT_PROJECT = os.getenv("LALA_PROJECT_PATH", "C:/Users/aemre/Desktop/ZEKY")

SSL_CTX = ssl._create_unverified_context()
EXECUTOR = ThreadPoolExecutor(max_workers=4)

sys.path.insert(0, str(Path(__file__).parent))
from agents import MasterAgent, DevAgent, QAAgent, DocAgent, DebugAgent, SecurityAgent
from main import parse_apply_blocks, apply_changes, git_commit_push

AGENT_MAP = {
    "master": MasterAgent, "dev": DevAgent, "qa": QAAgent,
    "doc": DocAgent, "debug": DebugAgent, "security": SecurityAgent,
}

# Bekleyen onay: {chat_id: (blocks, project, task, gate_ok)}
pending: dict[int, tuple] = {}

# Revizyon bekleniyor: {chat_id: (original_task, agent_key)}
awaiting_revision: dict[int, tuple] = {}


# ── Güvenlik Kapısı ───────────────────────────────────────────────────────────

import re as _re

_GATE_RULES = [
    (_re.compile(r"eval\s*\(", _re.I),                        "KRİTİK", "eval() — kod injection"),
    (_re.compile(r"exec\s*\(", _re.I),                        "KRİTİK", "exec() — kod injection"),
    (_re.compile(r"os\.system\s*\(", _re.I),                  "KRİTİK", "os.system() — komut injection"),
    (_re.compile(r"subprocess.*shell\s*=\s*True", _re.I),     "KRİTİK", "shell=True — komut injection"),
    (_re.compile(r"password\s*=\s*['\"][^'\"]{4,}", _re.I),   "YÜKSEK", "Hardcoded şifre"),
    (_re.compile(r"api_key\s*=\s*['\"][^'\"]{10,}", _re.I),   "YÜKSEK", "Hardcoded API anahtarı"),
    (_re.compile(r"pickle\.loads?\s*\(", _re.I),              "YÜKSEK", "pickle — güvensiz deserializasyon"),
    (_re.compile(r"verify\s*=\s*False", _re.I),               "ORTA",   "SSL doğrulama kapalı"),
]

def _extract_user_summary(output: str) -> str:
    """Ajan çıktısından KULLANICI ÖZETİ bölümünü çıkarır."""
    marker = "📋 KULLANICI ÖZETİ"
    if marker not in output:
        return ""
    start = output.find(marker)
    # Özet bölümünün sonu: ilk DOSYA: veya ``` bloğuna kadar
    end = output.find("\nDOSYA:", start)
    if end == -1:
        end = output.find("\n```", start)
    if end == -1:
        end = start + 600  # max 600 karakter
    return output[start:end].strip()


def _security_gate(blocks: list) -> tuple:
    """Üretilen kod bloklarını hızlı güvenlik taramasından geçirir. LLM gerekmez."""
    criticals, warnings = [], []
    for filepath, code in blocks:
        for pattern, severity, desc in _GATE_RULES:
            if pattern.search(code):
                entry = f"• `{filepath}`: {desc}"
                (criticals if severity == "KRİTİK" else warnings).append(entry)

    if criticals:
        lines = ["🔴 *Kritik Güvenlik Sorunu:*"] + criticals
        if warnings:
            lines += ["🟡 *Uyarılar:*"] + warnings
        return False, "\n".join(lines)

    if warnings:
        return True, "🟡 *Güvenlik Uyarıları (engelleyici değil):*\n" + "\n".join(warnings)

    return True, "🟢 Güvenlik taraması temiz."


# ── Telegram API ──────────────────────────────────────────────────────────────

def tg(method: str, **params) -> dict:
    url = f"https://api.telegram.org/bot{TOKEN}/{method}"
    encoded = {}
    for k, v in params.items():
        encoded[k] = json.dumps(v) if isinstance(v, (dict, list)) else str(v)
    data = urllib.parse.urlencode(encoded).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req, context=SSL_CTX, timeout=35) as r:
        return json.loads(r.read())


def send(chat_id: int, text: str, reply_markup=None, parse_mode: str = "Markdown"):
    params = {"chat_id": chat_id, "text": text}
    if parse_mode:
        params["parse_mode"] = parse_mode
    if reply_markup:
        params["reply_markup"] = json.dumps(reply_markup)
    try:
        tg("sendMessage", **params)
    except Exception as e:
        if parse_mode and "400" in str(e):
            try:
                plain = {k: v for k, v in params.items() if k != "parse_mode"}
                tg("sendMessage", **plain)
            except Exception as e2:
                log.error(f"sendMessage hatası: {e2}")
        else:
            log.error(f"sendMessage hatası: {e}")


def answer_callback(callback_id: str):
    try:
        tg("answerCallbackQuery", callback_query_id=callback_id)
    except Exception:
        pass


def edit_message(chat_id: int, message_id: int, text: str):
    try:
        tg("editMessageText", chat_id=chat_id, message_id=message_id,
           text=text, parse_mode="Markdown")
    except Exception as e:
        log.error(f"editMessage hatası: {e}")


# ── Komutlar ──────────────────────────────────────────────────────────────────

def cmd_durum(chat_id: int, _args: str):
    send(chat_id,
         "🟢 *LALA Bot aktif*\n\n"
         f"📁 Proje: `{DEFAULT_PROJECT}`\n\n"
         "*Nasıl kullanılır:*\n"
         "Ne istediğinizi doğal dilde yazın. Sistem otomatik yönlendirir.\n\n"
         "*Örnekler:*\n"
         "`Grants modülü ekle, hibe başvuru formu olsun`\n"
         "`src/seminar/engine.py dosyasındaki SMTP hatası neden oluşuyor?`\n"
         "`Analiz Motoru modülünü belgele`\n\n"
         "*Dosyaya yazmak için:* mesajın sonuna `--apply` ekle\n"
         "*GitHub push için:* `--apply --push` ekle\n\n"
         "`/iptal` — Bekleyen işlemi iptal et\n"
         "`/durum` — Bu menüyü göster")


def cmd_ajan(chat_id: int, agent_key: str, args: str):
    import concurrent.futures as cf
    parts = args.split()
    task  = " ".join(p for p in parts if p not in ("--apply", "--push")) or "Projeyi analiz et"

    send(chat_id, f"⏳ *{agent_key.upper()}* çalışıyor...\n`{task[:80]}`")

    try:
        AgentClass = AGENT_MAP[agent_key]
        agent = AgentClass(DEFAULT_PROJECT)
        context = {"apply": True}  # her zaman tam dosya formatı
        with cf.ThreadPoolExecutor(max_workers=1) as ex:
            fut = ex.submit(agent.run, task, context)
            try:
                result = fut.result(timeout=180)
            except cf.TimeoutError:
                send(chat_id, "⏰ Zaman aşımı: Ajan 3 dakika içinde cevap vermedi.")
                return
    except Exception as e:
        log.error(f"cmd_ajan hatası [{agent_key}]: {e}", exc_info=True)
        send(chat_id, f"❌ Ajan hatası: {e}")
        return

    if not result.ok():
        send(chat_id, f"❌ Hata: {result.error}")
        return

    # Çıktıyı gönder (4000 karakter sınırı)
    output = result.output
    for i in range(0, len(output), 4000):
        send(chat_id, output[i:i+4000], parse_mode=None)

    # Kod bloğu varsa otomatik butonlar göster — kullanıcı yazmak zorunda değil
    blocks = parse_apply_blocks(result.output)
    if not blocks:
        return

    gate_ok, gate_report = _security_gate(blocks)
    dosyalar = "\n".join(f"  • `{fp}` ({len(c.splitlines())} satır)" for fp, c in blocks)
    pending[chat_id] = (blocks, DEFAULT_PROJECT, task, gate_ok)

    if gate_ok:
        keyboard = {"inline_keyboard": [[
            {"text": "✅ Uygula",        "callback_data": "apply_yes"},
            {"text": "✅ Uygula + Push", "callback_data": "apply_push"},
        ], [
            {"text": "✏️ Revize Et",    "callback_data": "apply_revise"},
            {"text": "❌ İptal",         "callback_data": "apply_no"},
        ]]}
    else:
        keyboard = {"inline_keyboard": [[
            {"text": "✅ Uygula (push engellendi)", "callback_data": "apply_yes"},
            {"text": "✏️ Revize Et",               "callback_data": "apply_revise"},
        ], [
            {"text": "❌ İptal", "callback_data": "apply_no"},
        ]]}

    # Kullanıcı özetini çıkar (varsa)
    ozet = _extract_user_summary(result.output)
    ozet_bolum = f"{ozet}\n\n" if ozet else ""

    send(chat_id,
         f"{ozet_bolum}📂 *Değiştirilecek dosyalar:*\n{dosyalar}\n\n{gate_report}",
         reply_markup=keyboard)


def cmd_iptal(chat_id: int, _args: str):
    if pending.pop(chat_id, None):
        send(chat_id, "✅ Bekleyen işlem iptal edildi.")
    else:
        send(chat_id, "ℹ️ Bekleyen işlem yok.")


# ── Callback sorunu: inline buton ─────────────────────────────────────────────

def handle_callback(callback_id: str, chat_id: int, message_id: int, data: str):
    answer_callback(callback_id)
    if chat_id != ALLOWED_ID:
        return

    info = pending.pop(chat_id, None)
    if not info:
        edit_message(chat_id, message_id, "⚠️ Bekleyen işlem bulunamadı.")
        return

    blocks, project, task, gate_ok = info

    if data == "apply_no":
        edit_message(chat_id, message_id, "❌ İptal edildi.")
        return

    if data == "apply_revise":
        awaiting_revision[chat_id] = ("dev", task)
        edit_message(chat_id, message_id,
                     "✏️ *Ne değiştirilsin?*\n\nDüzeltme isteğinizi yazın — ajan yeniden üretecek.")
        return

    push = (data == "apply_push") and gate_ok

    edit_message(chat_id, message_id, "⏳ Dosyalar yazılıyor...")
    try:
        changed = apply_changes(project, blocks)
        yazilan = "\n".join(f"  ✓ `{f}`" for f in changed)
        if push and changed:
            ok = git_commit_push(project, task, changed, push=True)
            push_sonuc = "\n✅ GitHub'a push edildi." if ok else "\n⚠️ Push başarısız."
        elif data == "apply_push" and not gate_ok:
            push_sonuc = "\n⛔ Güvenlik sorunu nedeniyle push engellendi."
        else:
            push_sonuc = ""
        edit_message(chat_id, message_id, f"✅ *Uygulandı:*\n{yazilan}{push_sonuc}")
    except Exception as e:
        edit_message(chat_id, message_id, f"❌ Hata: {e}")


# ── Update işleyici ───────────────────────────────────────────────────────────

COMMANDS = {
    "durum": cmd_durum, "dev": cmd_ajan, "qa": cmd_ajan,
    "doc": cmd_ajan, "debug": cmd_ajan, "master": cmd_ajan,
    "security": cmd_ajan, "iptal": cmd_iptal,
}

def process_update(update: dict):
    # Callback query (inline buton)
    if "callback_query" in update:
        cq = update["callback_query"]
        chat_id    = cq["message"]["chat"]["id"]
        message_id = cq["message"]["message_id"]
        cb_id      = cq["id"]
        data       = cq.get("data", "")
        log.info(f"Callback: chat_id={chat_id} data={data}")
        if chat_id == ALLOWED_ID:
            handle_callback(cb_id, chat_id, message_id, data)
        return

    # Mesaj
    msg = update.get("message") or update.get("edited_message")
    if not msg:
        return

    chat_id = msg["chat"]["id"]
    text    = msg.get("text", "")
    log.info(f"Mesaj: chat_id={chat_id} text={text!r}")

    if chat_id != ALLOWED_ID:
        log.warning(f"Yetkisiz chat_id: {chat_id}")
        return

    # Serbest metin
    if not text.startswith("/"):
        if chat_id in awaiting_revision:
            # Revizyon modu: orijinal görevi + yeni talebi birleştir
            agent_key, original_task = awaiting_revision.pop(chat_id)
            revised_task = f"{original_task}\n\nKULLANICI REVİZYONU: {text}"
            send(chat_id, f"✏️ *Revize ediliyor...*\n`{text[:80]}`")
            EXECUTOR.submit(cmd_ajan, chat_id, agent_key, revised_task)
        else:
            # Normal mod: Master ajan yönlendirir
            EXECUTOR.submit(cmd_ajan, chat_id, "master", text)
        return

    # Slash komutları
    parts   = text.lstrip("/").split(None, 1)
    cmd     = parts[0].split("@")[0].lower()
    args    = parts[1] if len(parts) > 1 else ""

    if cmd not in COMMANDS:
        send(chat_id, f"Bilinmeyen komut: /{cmd}\n/durum yazarak kullanım rehberini görün.")
        return

    fn = COMMANDS[cmd]
    if cmd in ("dev", "qa", "doc", "debug", "master", "security"):
        EXECUTOR.submit(cmd_ajan, chat_id, cmd, args)
    else:
        EXECUTOR.submit(fn, chat_id, args)


# ── Ana döngü ─────────────────────────────────────────────────────────────────

def main():
    if not TOKEN:
        print("HATA: TELEGRAM_BOT_TOKEN bulunamadı.")
        sys.exit(1)

    # Webhook sil
    tg("deleteWebhook", drop_pending_updates=False)
    log.info(f"LALA Bot başlatıldı. Yetkili chat ID: {ALLOWED_ID}")

    offset = 0
    while True:
        try:
            resp = tg("getUpdates", offset=offset, timeout=20, limit=10,
                      allowed_updates=["message", "callback_query"])
            log.info(f"API yanıtı: ok={resp.get('ok')} result_count={len(resp.get('result', []))} raw={str(resp)[:400]}")
            updates = resp.get("result", [])
            for u in updates:
                log.info(f"RAW update: {json.dumps(u)[:300]}")
                offset = u["update_id"] + 1
                try:
                    process_update(u)
                except Exception as e:
                    log.error(f"Update işleme hatası: {e}", exc_info=True)
        except KeyboardInterrupt:
            log.info("Bot durduruluyor.")
            EXECUTOR.shutdown(wait=False)
            break
        except Exception as e:
            log.error(f"Polling hatası: {e}")
            import time; time.sleep(3)


if __name__ == "__main__":
    main()
