"""Doc Agent — Dokümantasyon, README, CHANGELOG, docstring."""
from __future__ import annotations
from typing import Dict, Optional
from .base import BaseAgent, AgentResult


class DocAgent(BaseAgent):

    ROLE = "doc"
    SYSTEM_PROMPT = """Sen teknik bir belge yazarısın.
Görevin: kaynak kodu okuyup anlaşılır Türkçe dokümantasyon üretmek.
İlkeler:
- README: kullanıcı odaklı, kurulum + kullanım + örnekler
- CHANGELOG: developer odaklı, ne değişti + neden
- Docstring: kısa, net, parametre açıklamalı (numpy stili)
- Gereksiz tekrar yapma, kodu özetleme yeterli
Yanıtın direkt dosya içeriği olsun, ek açıklama ekleme."""

    def run(self, task: str, context: Optional[Dict] = None) -> AgentResult:
        ctx = context or {}
        files_read = []

        doc_type = ctx.get("doc_type", "genel")  # readme / changelog / docstring / genel

        if "files" in ctx:
            code_ctx = self._build_code_context(
                {f: self.read_file(f) for f in ctx["files"]}
            )
            files_read = ctx["files"]
        elif doc_type == "readme":
            # README için tüm yapıyı ver
            all_py = self.read_files("**/*.py")
            readme = self.read_file("README.md") if (self.project_path / "README.md").exists() else ""
            code_ctx = f"Mevcut README:\n{readme}\n\nKod:\n" + self._build_code_context(all_py)
            files_read = list(all_py.keys())
        else:
            py_files = self.read_files("**/*.py")
            code_ctx = self._build_code_context(py_files)
            files_read = list(py_files.keys())

        prompt = f"""Proje: {self.project_path.name}
Dokümantasyon tipi: {doc_type}

{code_ctx}

Görev: {task}"""

        try:
            output = self._ask(prompt, temperature=0.4)
            return AgentResult(
                agent="DocAgent",
                task=task,
                output=output,
                files_read=files_read,
            )
        except Exception as e:
            return AgentResult(agent="DocAgent", task=task, output="", error=str(e))
