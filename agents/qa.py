"""QA Agent — Test yazma, kod kalite kontrolü, review."""
from __future__ import annotations
from typing import Dict, Optional
from .base import BaseAgent, AgentResult, ZEKY_CONTEXT


class QAAgent(BaseAgent):

    ROLE = "qa"

    SYSTEM_PROMPT = f"""Sen ZEKY projesinin kalite güvence (QA) uzmanısın.
{ZEKY_CONTEXT}

## GÖREVIN

Kodu incele — sadece hata bul değil, ZEKY'nin akademik kullanıcısı için ne anlama geldiğini düşün:
- Bir farmakolog bu modülü kullandığında ne sorunla karşılaşır?
- Eksik hata mesajları, boş ekranlar, çöken sayfalar kabul edilemez
- Streamlit session_state hataları, import sorunları, veri tipi uyumsuzlukları

## ÇIKTI FORMATI

📋 KULLANICI ÖZETİ
─────────────────────
Kontrol ettim : <neyi inceledim>
Sonuç         : <iyi | dikkat edilmeli | sorunlu>
Kullanıcıya etkisi: <bu sorun olursa ne olur — teknik terim kullanma>
Acil mi       : <evet/hayır + neden>

KALİTE PUANI: <0-10> — <tek cümle gerekçe>

KRİTİK SORUNLAR (varsa):
- [KRİTİK] <sorun> → <düzeltme>

UYARILAR (varsa):
- [UYARI] <sorun> → <öneri>

TEST KODU:
```python
# pytest testleri — çalışır halde
```"""

    def run(self, task: str, context: Optional[Dict] = None) -> AgentResult:
        ctx = context or {}
        files_read = []

        if "files" in ctx:
            code_ctx = self._build_code_context(
                {f: self.read_file(f) for f in ctx["files"]}
            )
            files_read = ctx["files"]
        else:
            py_files = self.read_files("**/*.py")
            code_ctx = self._build_code_context(py_files)
            files_read = list(py_files.keys())

        prompt = f"""Proje: {self.project_path.name}

Kod:
{code_ctx}

QA İsteği: {task}

ZEKY'nin farmakoloji kullanıcısı perspektifinden kodu incele, bulguları raporla."""

        try:
            output = self._ask(prompt, temperature=0.2)
            return AgentResult(
                agent="QAAgent",
                task=task,
                output=output,
                files_read=files_read,
            )
        except Exception as e:
            return AgentResult(agent="QAAgent", task=task, output="", error=str(e))
