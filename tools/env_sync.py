"""
DO sunucusunu .env için merkez alır; pull/push yapar.

  python tools/env_sync.py          # DO → yerel (default)
  python tools/env_sync.py --push   # yerel → DO
"""
from __future__ import annotations
import subprocess, sys, os
from pathlib import Path

DO_HOST     = "root@165.245.213.201"
SSH_KEY     = Path.home() / ".ssh" / "id_ed25519"
SSH_OPTS    = ["-i", str(SSH_KEY), "-o", "StrictHostKeyChecking=no",
               "-o", "ConnectTimeout=15"]

DO_ENV_PATHS = ["/root/LALA/.env", "/root/ZEKY/.env"]

LOCAL_ENV_CANDIDATES = [
    Path(__file__).parent.parent / ".env",           # lala-agents/.env
    Path("C:/LALA/lala-agents/.env"),
    Path("C:/Users/aemre/Desktop/ZEKY/../lala-agents/.env"),
]
ZEKY_ENV_CANDIDATES = [
    Path("C:/LALA/ZEKY/.env"),
    Path("C:/Users/aemre/Desktop/ZEKY/.env"),
]


def _parse(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, _, v = line.partition("=")
            out[k.strip()] = v.strip()
    return out


def _render(data: dict[str, str]) -> str:
    return "\n".join(f"{k}={v}" for k, v in data.items()) + "\n"


def _ssh_read(remote_path: str) -> str:
    r = subprocess.run(
        ["ssh"] + SSH_OPTS + [DO_HOST, f"cat {remote_path}"],
        capture_output=True, text=True, timeout=30,
    )
    if r.returncode != 0:
        raise RuntimeError(f"SSH okuma hatası ({remote_path}): {r.stderr.strip()}")
    return r.stdout


def _ssh_write(remote_path: str, content: str):
    r = subprocess.run(
        ["ssh"] + SSH_OPTS + [DO_HOST, f"tee {remote_path} > /dev/null"],
        input=content, capture_output=True, text=True, timeout=30,
    )
    if r.returncode != 0:
        raise RuntimeError(f"SSH yazma hatası ({remote_path}): {r.stderr.strip()}")


def _find_local(candidates: list[Path]) -> Path | None:
    return next((p for p in candidates if p.exists()), None)


def pull():
    """DO'daki /root/LALA/.env → yerel .env dosyaları."""
    print("DO'dan .env çekiliyor...")
    remote_raw = _ssh_read(DO_ENV_PATHS[0])
    remote     = _parse(remote_raw)
    print(f"  {len(remote)} anahtar alındı.")

    local_path = _find_local(LOCAL_ENV_CANDIDATES)
    if not local_path:
        local_path = Path(__file__).parent.parent / ".env"
        print(f"  Yeni dosya oluşturulacak: {local_path}")
        local = {}
    else:
        local = _parse(local_path.read_text(encoding="utf-8"))

    merged = {**local, **remote}   # DO değerleri kazanır
    local_path.write_text(_render(merged), encoding="utf-8")
    print(f"✅ {local_path} güncellendi.")

    zeky_path = _find_local(ZEKY_ENV_CANDIDATES)
    if zeky_path:
        zeky = _parse(zeky_path.read_text(encoding="utf-8"))
        zeky_merged = {**zeky, **remote}
        zeky_path.write_text(_render(zeky_merged), encoding="utf-8")
        print(f"✅ {zeky_path} güncellendi.")


def push():
    """Yerel .env → DO'daki tüm .env dosyaları."""
    local_path = _find_local(LOCAL_ENV_CANDIDATES)
    if not local_path:
        print("❌ Yerel .env bulunamadı.")
        sys.exit(1)

    content = local_path.read_text(encoding="utf-8")
    for remote_path in DO_ENV_PATHS:
        # Önce uzaktaki mevcut değerleri çek, yerel ile birleştir
        try:
            remote = _parse(_ssh_read(remote_path))
        except Exception:
            remote = {}
        local = _parse(content)
        merged = {**remote, **local}   # yerel kazanır
        _ssh_write(remote_path, _render(merged))
        print(f"✅ DO:{remote_path} güncellendi.")


if __name__ == "__main__":
    if "--push" in sys.argv:
        push()
    else:
        pull()
