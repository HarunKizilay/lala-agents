"""
Windows'ta oturum açılınca env_sync.py'yi otomatik çalıştıracak
Görev Zamanlayıcı görevi kurar.

  python tools/setup_startup.py          # görevi kur
  python tools/setup_startup.py --remove # görevi kaldır
"""
import subprocess, sys
from pathlib import Path

TASK_NAME   = "LALA_EnvSync"
PYTHON      = sys.executable
SCRIPT      = str(Path(__file__).parent / "env_sync.py")


def install():
    # Mevcut görevi sil (güncelleme için)
    subprocess.run(
        ["schtasks", "/Delete", "/TN", TASK_NAME, "/F"],
        capture_output=True,
    )

    result = subprocess.run([
        "schtasks", "/Create",
        "/TN",  TASK_NAME,
        "/TR",  f'"{PYTHON}" "{SCRIPT}"',
        "/SC",  "ONLOGON",
        "/RL",  "HIGHEST",
        "/F",
    ], capture_output=True, text=True)

    if result.returncode == 0:
        print(f"✅ Görev kuruldu: {TASK_NAME}")
        print(f"   Her login'de DO'dan .env otomatik çekilecek.")
        print(f"   Manuel çalıştırmak için: python \"{SCRIPT}\"")
    else:
        print(f"❌ Görev kurulamadı:\n{result.stderr or result.stdout}")
        print("\nYönetici olarak çalıştırmayı deneyin:")
        print(f'  schtasks /Create /TN {TASK_NAME} /TR "{PYTHON} {SCRIPT}" /SC ONLOGON /RL HIGHEST /F')


def remove():
    result = subprocess.run(
        ["schtasks", "/Delete", "/TN", TASK_NAME, "/F"],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        print(f"✅ Görev kaldırıldı: {TASK_NAME}")
    else:
        print(f"❌ Görev bulunamadı veya kaldırılamadı.")


if __name__ == "__main__":
    if "--remove" in sys.argv:
        remove()
    else:
        install()
