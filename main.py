"""
LALA Ajan Sistemi — CLI
Kullanım: python main.py [ajan] "görev" [--project YOL]

Örnekler:
  python main.py "ZEKY analiz motoru için unit test yaz"
  python main.py security "güvenlik taraması yap"
  python main.py dev "advisor.py'ye cache ekle" --project C:/Users/aemre/Desktop/ZEKY
  python main.py all "tam proje denetimi" --project C:/Users/aemre/Desktop/ZEKY
"""
from __future__ import annotations

import sys, io
# Windows konsolunda UTF-8 çıktı
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Proje köküne sys.path ekle
sys.path.insert(0, str(Path(__file__).parent))

from agents import (
    MasterAgent, DevAgent, QAAgent, DocAgent, DebugAgent, SecurityAgent
)

# ── Varsayılan proje ───────────────────────────────────────────────────────────
DEFAULT_PROJECT = "C:/Users/aemre/Desktop/ZEKY"

AGENT_MAP = {
    "master":   MasterAgent,
    "dev":      DevAgent,
    "qa":       QAAgent,
    "doc":      DocAgent,
    "debug":    DebugAgent,
    "security": SecurityAgent,
    "all":      MasterAgent,   # MasterAgent tüm ajanları çalıştırır
}

AGENT_KEYS = list(AGENT_MAP.keys())


def print_banner():
    print("=" * 60)
    print("  LALA Ajan Sistemi — 6 Ajan")
    print("  Master · Dev · QA · Doc · Debug · Security")
    print("=" * 60)


def save_result(result, output_dir: Path):
    """Sonucu LALA log klasörüne kaydeder."""
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = output_dir / f"{ts}_{result.agent}_{result.task[:30].replace(' ','_')}.md"
    content = f"# {result.agent} — {result.task}\n\n"
    content += f"**Tarih:** {result.timestamp}\n"
    content += f"**Proje:** —\n"
    if result.files_read:
        content += f"**Okunan dosyalar:** {', '.join(result.files_read[:10])}\n"
    content += "\n---\n\n"
    content += result.output
    fname.write_text(content, encoding="utf-8")
    return fname


def parse_apply_blocks(output: str) -> list:
    """DOSYA:/FILE:/### path + kod bloklarını çıkarır."""
    blocks = []
    # Format 1: DOSYA: path\n```python\n...\n```
    pattern1 = r'(?:DOSYA|FILE|Dosya):\s*([^\n`]+?)\s*\n```(?:python|py)?\n(.*?)```'
    for m in re.finditer(pattern1, output, re.DOTALL):
        fp = m.group(1).strip().strip("*`").replace("\\", "/")
        code = m.group(2).rstrip("\n")
        if fp and code:
            blocks.append((fp, code))
    if blocks:
        return blocks
    # Format 2: ### path.py\n```python\n...\n```
    pattern2 = r'#{1,3}\s*([\w./\\-]+\.py)\s*\n```(?:python|py)?\n(.*?)```'
    for m in re.finditer(pattern2, output, re.DOTALL):
        fp = m.group(1).strip().replace("\\", "/")
        code = m.group(2).rstrip("\n")
        if fp and code:
            blocks.append((fp, code))
    return blocks


def apply_changes(project_path: str, blocks: list) -> list:
    """Kod bloklarını dosyalara yazar, değiştirilen dosya listesini döner."""
    changed = []
    base = Path(project_path)
    for filepath, code in blocks:
        full_path = base / filepath
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(code, encoding="utf-8")
        print(f"  ✓ Yazıldı: {filepath}")
        changed.append(filepath)
    return changed


def git_commit_push(project_path: str, task: str, changed_files: list, push: bool) -> tuple:
    """Değiştirilen dosyaları git'e ekler, commit atar, opsiyonel push yapar.
    Returns: (success: bool, message: str)
    """
    base = Path(project_path)
    try:
        for f in changed_files:
            subprocess.run(["git", "add", f], cwd=base, check=True)

        msg = (
            f"feat: LALA Dev ajanı — {task[:60]}\n\n"
            f"Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
        )
        r = subprocess.run(["git", "commit", "-m", msg], cwd=base,
                           capture_output=True, text=True)
        if r.returncode != 0:
            err = r.stderr.strip() or r.stdout.strip()
            return False, f"Commit hatası: {err[:300]}"

        if push:
            # Push öncesi pull — local geride kalmasın
            subprocess.run(["git", "pull", "origin", "main", "--no-rebase"],
                           cwd=base, capture_output=True, text=True)
            r = subprocess.run(["git", "push", "origin", "main"], cwd=base,
                               capture_output=True, text=True)
            if r.returncode != 0:
                err = r.stderr.strip() or r.stdout.strip()
                return False, f"Push hatası: {err[:300]}"
            return True, "GitHub'a push edildi."
        return True, "Commit edildi (push yapılmadı)."
    except Exception as e:
        return False, f"Git hatası: {e}"


def main():
    parser = argparse.ArgumentParser(
        description="LALA Ajan Sistemi",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "agent_or_task",
        nargs="?",
        help="Ajan adı (master/dev/qa/doc/debug/security/all) veya direkt görev",
    )
    parser.add_argument(
        "task",
        nargs="?",
        help="Görev açıklaması (ajan adı verilmişse)",
    )
    parser.add_argument(
        "--project", "-p",
        default=DEFAULT_PROJECT,
        help=f"Proje yolu (varsayılan: {DEFAULT_PROJECT})",
    )
    parser.add_argument(
        "--files", "-f",
        nargs="*",
        help="Sadece belirtilen dosyalara odaklan",
    )
    parser.add_argument(
        "--error", "-e",
        default="",
        help="Debug ajanı için hata mesajı / traceback",
    )
    parser.add_argument(
        "--save", "-s",
        action="store_true",
        help="Sonucu LALA'ya kaydet",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Çıktıyı JSON formatında ver",
    )
    parser.add_argument(
        "--apply", "-a",
        action="store_true",
        help="Dev ajanı çıktısını dosyalara uygula (tam dosya modu)",
    )
    parser.add_argument(
        "--push",
        action="store_true",
        help="--apply ile birlikte kullanılır: değişiklikleri GitHub'a push et",
    )

    args = parser.parse_args()

    # Argüman mantığı: agent_or_task hem ajan adı hem de görev olabilir
    if args.agent_or_task in AGENT_KEYS:
        agent_key = args.agent_or_task
        task = args.task or ""
    else:
        agent_key = "master"
        task = " ".join(filter(None, [args.agent_or_task, args.task]))

    if not task:
        print("HATA: Görev belirtilmedi.")
        print('Örnek: python main.py "güvenlik taraması yap"')
        sys.exit(1)

    print_banner()
    print(f"Ajan    : {agent_key.upper()}")
    print(f"Görev   : {task}")
    print(f"Proje   : {args.project}")
    print("-" * 60)

    # Context oluştur
    context = {}
    if args.files:
        context["files"] = args.files
    if args.error:
        context["error"] = args.error
    if args.apply:
        context["apply"] = True
    if agent_key == "all":
        context["agents"] = ["dev", "qa", "doc", "debug", "security"]

    # Ajanı çalıştır
    try:
        AgentClass = AGENT_MAP[agent_key]
        agent = AgentClass(args.project)

        if agent_key == "all":
            # MasterAgent tüm ajanları çalıştırır
            from agents.master import MasterAgent as MA
            agent = MA(args.project)

        print("Çalışıyor...\n")
        result = agent.run(task, context)

    except ValueError as e:
        print(f"HATA: {e}")
        sys.exit(1)

    # Çıktı
    if args.json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(result.output if result.ok() else f"HATA: {result.error}")

    # --apply: çıktıdaki kodu dosyalara yaz
    if args.apply and result.ok():
        blocks = parse_apply_blocks(result.output)
        if not blocks:
            print("\n[APPLY] Uygulanacak kod bloğu bulunamadı.")
            print("  İpucu: Sadece 'dev' ajanıyla çalışır.")
        else:
            print(f"\n{'='*60}")
            print(f"[APPLY] Ajan şu dosyaları değiştirmek istiyor:")
            for filepath, code in blocks:
                lines = len(code.splitlines())
                print(f"  • {filepath}  ({lines} satır)")
            if args.push:
                print(f"  → Onaylanırsa GitHub'a push edilecek.")
            print(f"{'='*60}")
            onay = input("Uygulansın mı? [e/h]: ").strip().lower()
            if onay == "e":
                print()
                changed = apply_changes(args.project, blocks)
                if changed:
                    git_commit_push(args.project, task, changed, push=args.push)
            else:
                print("  İptal edildi, dosyalar değiştirilmedi.")

    # --save: sonucu logla
    if args.save:
        log_dir = Path(__file__).parent / "logs"
        saved = save_result(result, log_dir)
        print(f"\nKaydedildi: {saved}")

    return 0 if result.ok() else 1


if __name__ == "__main__":
    sys.exit(main())
