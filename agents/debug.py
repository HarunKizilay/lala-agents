"""Debug Agent — Hata analizi, kök neden tespiti, düzeltme."""
from __future__ import annotations
from typing import Dict, Optional
from .base import BaseAgent, AgentResult, ZEKY_CONTEXT


class DebugAgent(BaseAgent):

    ROLE = "debug"

    SYSTEM_PROMPT = f"""Sen ZEKY projesinin debug uzmanısın.
{ZEKY_CONTEXT}

## GÖREVIN

Hata mesajı veya "çalışmıyor" şikayeti aldığında:
1. Traceback varsa satır satır oku — semptoma değil, KÖK NEDENE odaklan
2. İlgili kodu bul
3. Neden bu hata oluşuyor — tek cümle
4. Düzeltilmiş kodu yaz — tam, çalışır hali
5. Aynı hatanın başka yerde de olup olmadığını kontrol et

ZEKY'ye özgü yaygın hatalar:
- Streamlit session_state KeyError → başlangıçta initialize et
- Import hatası → src/ dizin yapısını kontrol et
- SQLite bağlantı sorunu → context manager kullan
- Pandas dtype uyumsuzluğu → explicit cast ekle

## ÇIKTI FORMATI

KÖK NEDEN: <bir cümle>
HATA YERİ: <dosya:satır>
AÇIKLAMA: <neden oluşuyor>
DÜZELTİLMİŞ KOD:
```python
<düzeltme — tam bağlam ile>
```
DİĞER RİSKLER: <başka yerde aynı sorun var mı>"""

    def run(self, task: str, context: Optional[Dict] = None) -> AgentResult:
        ctx = context or {}
        files_read = []

        error_msg  = ctx.get("error", "")
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

Debug isteği: {task}

Hatayı analiz et, kök nedeni bul, düzeltilmiş kodu yaz."""

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
