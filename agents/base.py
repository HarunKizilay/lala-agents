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


MAX_FILE_CHARS = 12_000   # LLM'e gönderilecek max karakter / dosya
MAX_FILES      = 20       # Tek seferde okunacak max dosya


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

    def _ask(self, prompt: str, temperature: float = 0.3) -> str:
        return ask(prompt, system=self.SYSTEM_PROMPT, temperature=temperature)

    def _build_code_context(self, files: Dict[str, str]) -> str:
        """Dosya içeriklerini LLM'e gönderilecek metin bloğuna çevirir."""
        parts = []
        for path, content in files.items():
            parts.append(f"### {path}\n```\n{content}\n```")
        return "\n\n".join(parts)

    # ── soyut metot ────────────────────────────────────────────────────────────

    @abstractmethod
    def run(self, task: str, context: Optional[Dict] = None) -> AgentResult:
        """Görevi çalıştırır, AgentResult döner."""
