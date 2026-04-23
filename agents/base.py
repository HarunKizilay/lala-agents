"""
BaseAgent — tüm ajanların ortak altyapısı.
Herhangi bir proje klasörüne yönlendirilebilir.
"""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from llm.client import ask


MAX_FILE_CHARS   = 4_000  # LLM'e gönderilecek max karakter / dosya
MAX_FILES        = 10     # Tek seferde okunacak max dosya
MAX_TOTAL_CHARS  = 30_000 # Tüm prompt için üst sınır (API payload limiti)

ZEKY_CONTEXT = """
## ZEKY Projesi Bağlamı
- **Ne:** Selçuk Üniversitesi Eczacılık Fakültesi için Python+Streamlit tabanlı farmakoloji AI asistanı
- **Kullanıcı:** Prof. Dr. Harun Kızılay — farmakolog, Python öğreniyor, isteklerini doğal dilde yazar
- **Teknoloji:** Python, Streamlit, SQLite, pandas, scikit-learn, plotly, pingouin, lifelines
- **Mevcut modüller:** Giriş (şifreli), Advisor (araştırma önerisi), Makale Yazım, ML/ANN Lab,
  Hakem Simülatörü, Haftalık Seminer, Analiz Motoru (7 sekmeli istatistik)
- **Yapılmakta:** Grants (hibe başvurusu), Research Types (araştırma sınıflandırma)
- **Kod stili:** Türkçe UI metinleri ve açıklamalar, İngilizce kod, src/ dizin yapısı,
  her modül src/<modül>/ altında, app.py ana sayfa yönlendirmesi
- **Sunucu:** DigitalOcean 165.245.213.201, zeky.service, port 8501
"""


class AgentResult:
    def __init__(self, agent: str, task: str, output: str,
                 files_read: List[str] = None, error: str = None):
        self.agent      = agent
        self.task       = task
        self.output     = output
        self.files_read = files_read or []
        self.error      = error
        self.timestamp  = datetime.now().isoformat(timespec="seconds")

    def ok(self) -> bool:
        return self.error is None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent":      self.agent,
            "task":       self.task,
            "output":     self.output,
            "files_read": self.files_read,
            "error":      self.error,
            "timestamp":  self.timestamp,
        }

    def __str__(self) -> str:
        header = f"[{self.agent}] {self.task}"
        if self.error:
            return f"{header}\nHATA: {self.error}"
        return f"{header}\n{self.output}"


class BaseAgent(ABC):
    """Tüm ajanların türediği soyut sınıf."""

    ROLE: str = ""          # Alt sınıf tanımlar
    SYSTEM_PROMPT: str = "" # Alt sınıf tanımlar

    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        if not self.project_path.exists():
            raise ValueError(f"Proje klasörü bulunamadı: {project_path}")

    # ── dosya işlemleri ────────────────────────────────────────────────────────

    def read_file(self, rel_path: str) -> str:
        """Proje içindeki dosyayı okur, çok uzunsa kırpar."""
        full = self.project_path / rel_path
        if not full.exists():
            return f"[DOSYA YOK: {rel_path}]"
        text = full.read_text(encoding="utf-8", errors="ignore")
        if len(text) > MAX_FILE_CHARS:
            text = text[:MAX_FILE_CHARS] + f"\n... [{len(text)-MAX_FILE_CHARS} karakter kırpıldı]"
        return text

    def list_files(self, pattern: str = "**/*.py",
                   exclude_dirs: List[str] = None) -> List[str]:
        """Proje dosyalarını glob pattern ile listeler."""
        exclude = set(exclude_dirs or ["__pycache__", ".git", "venv", "node_modules",
                                        ".venv", "dist", "build"])
        files = []
        for p in self.project_path.glob(pattern):
            if not any(part in exclude for part in p.parts):
                files.append(str(p.relative_to(self.project_path)))
        return sorted(files)[:MAX_FILES]

    def read_files(self, pattern: str = "**/*.py") -> Dict[str, str]:
        """Birden fazla dosya okur, dict olarak döner."""
        return {f: self.read_file(f) for f in self.list_files(pattern)}

    # ── LLM çağrısı ────────────────────────────────────────────────────────────

    def _ask(self, prompt: str, temperature: float = 0.3, system_override: str = "") -> str:
        system = system_override or self.SYSTEM_PROMPT
        return ask(prompt, system=system, temperature=temperature)

    def _build_code_context(self, files: Dict[str, str]) -> str:
        """Dosya içeriklerini LLM'e gönderilecek metin bloğuna çevirir (boyut sınırlı)."""
        parts = []
        total = 0
        for path, content in files.items():
            block = f"### {path}\n```\n{content}\n```"
            if total + len(block) > MAX_TOTAL_CHARS:
                parts.append(f"### ... (boyut sınırı nedeniyle {len(files) - len(parts)} dosya atlandı)")
                break
            parts.append(block)
            total += len(block)
        return "\n\n".join(parts)

    # ── soyut metot ────────────────────────────────────────────────────────────

    @abstractmethod
    def run(self, task: str, context: Optional[Dict] = None) -> AgentResult:
        """Görevi çalıştırır, AgentResult döner."""
