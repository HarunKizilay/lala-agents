"""QA Agent — Test yazma, kod kalite kontrolü, review."""
from __future__ import annotations
from typing import Dict, Optional
from .base import BaseAgent, AgentResult


class QAAgent(BaseAgent):

    ROLE = "qa"
    SYSTEM_PROMPT = """Sen bir yazılım kalite güvence (QA) uzmanısın.
Görevin: kodu incelemek, hataları bulmak, testler yazmak.
Odak alanların:
- Mantık hataları ve edge case'ler
- Test coverage eksiklikleri
- Hatalı veya eksik hata yönetimi
- Performans sorunları
- pytest ile yazılmış, çalışır test dosyaları

Yanıt formatı:
KALİTE PUANI: <0-10>
BULGULAR:
- [KRİTİK/UYARI/ÖNERİ] <bulgu>
TEST KODU:
```python
<pytest testleri>
```
ÖZET: <genel değerlendirme>"""

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

QA Görevi: {task}

Kodu incele, bulguları raporla ve gerekirse pytest testleri yaz."""

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
