"""Dev Agent — Kod yazma, refactoring, özellik ekleme."""
from __future__ import annotations
from typing import Dict, Optional
from .base import BaseAgent, AgentResult


class DevAgent(BaseAgent):

    ROLE = "dev"
    SYSTEM_PROMPT = """Sen kıdemli bir Python yazılım geliştiricisisin.
Görevin: verilen projenin mevcut kodunu anlayıp, istenen kodu yazmak veya değiştirmek.
Kurallar:
- Sadece değişen/eklenen kodu yaz. Açıklama eklemek yerine iyi isimler kullan.
- Mevcut mimariyle uyumlu ol. Gereksiz bağımlılık ekleme.
- Çıktın her zaman çalışır durumda olmalı.
- Türkçe yorum ekleme, kod İngilizce; açıklamaların Türkçe olabilir.
- Yanıtını şu formatta ver:
  DOSYA: <dosya_yolu>
  ```python
  <kod>
  ```
  AÇIKLAMA: <ne yaptığın, neden>"""

    def run(self, task: str, context: Optional[Dict] = None) -> AgentResult:
        ctx = context or {}
        files_read = []

        # İlgili dosyaları bul
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

Mevcut kod:
{code_ctx}

Görev: {task}

Yukarıdaki projeye göre bu görevi gerçekleştir."""

        try:
            output = self._ask(prompt, temperature=0.2)
            return AgentResult(
                agent="DevAgent",
                task=task,
                output=output,
                files_read=files_read,
            )
        except Exception as e:
            return AgentResult(agent="DevAgent", task=task, output="", error=str(e))
