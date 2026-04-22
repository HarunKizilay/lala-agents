"""Debug Agent — Hata analizi, kök neden tespiti, düzeltme önerisi."""
from __future__ import annotations
from typing import Dict, Optional
from .base import BaseAgent, AgentResult


class DebugAgent(BaseAgent):

    ROLE = "debug"
    SYSTEM_PROMPT = """Sen bir uzman yazılım debug uzmanısın.
Görevin: hata mesajlarını ve kodu analiz edip kök nedeni bulmak ve düzeltmek.
Yaklaşımın:
1. Hata mesajını (traceback) satır satır oku
2. İlgili kodu bul
3. Kök nedeni açıkla (semptom değil, neden)
4. Düzeltilmiş kodu yaz
5. Aynı hatanın başka yerde olup olmadığını kontrol et

Yanıt formatı:
KÖK NEDEN: <bir cümle>
HATA YERİ: <dosya:satır>
AÇIKLAMA: <neden bu hata oluşuyor>
DÜZELTİLMİŞ KOD:
```python
<düzeltme>
```
DİĞER RİSKLER: <başka yerde aynı sorun var mı>"""

    def run(self, task: str, context: Optional[Dict] = None) -> AgentResult:
        ctx = context or {}
        files_read = []

        error_msg = ctx.get("error", "")
        traceback  = ctx.get("traceback", "")

        if "files" in ctx:
            code_ctx = self._build_code_context(
                {f: self.read_file(f) for f in ctx["files"]}
            )
            files_read = ctx["files"]
        else:
            py_files = self.read_files("**/*.py")
            code_ctx = self._build_code_context(py_files)
            files_read = list(py_files.keys())

        error_section = ""
        if error_msg or traceback:
            error_section = f"\nHATA MESAJI:\n```\n{traceback or error_msg}\n```\n"

        prompt = f"""Proje: {self.project_path.name}
{error_section}
Kod:
{code_ctx}

Debug görevi: {task}

Hatayı analiz et, kök nedeni bul ve düzeltilmiş kodu yaz."""

        try:
            output = self._ask(prompt, temperature=0.1)
            return AgentResult(
                agent="DebugAgent",
                task=task,
                output=output,
                files_read=files_read,
            )
        except Exception as e:
            return AgentResult(agent="DebugAgent", task=task, output="", error=str(e))
