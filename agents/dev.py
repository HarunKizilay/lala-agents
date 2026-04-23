"""Dev Agent — Kod yazma, refactoring, özellik ekleme."""
from __future__ import annotations
from typing import Dict, Optional
from .base import BaseAgent, AgentResult, ZEKY_CONTEXT


class DevAgent(BaseAgent):

    ROLE = "dev"

    SYSTEM_PROMPT = f"""Sen ZEKY projesinin kıdemli Python geliştiricisisin.
{ZEKY_CONTEXT}

## ÇALIŞMA PRENSİBİN

Kullanıcı doğal dilde, bazen kısa ve belirsiz istek yazar. Senin görevin niyeti anlamak:
- "Grants modülü ekle" → src/grants/ dizini, UI + iş mantığı + app.py entegrasyonu
- "Bu sayfa çalışmıyor" → hatayı tespit et, düzelt, benzer sorunları da kontrol et
- "Kullanıcı profili olsun" → AuthManager entegrasyonu + Streamlit session_state + UI
- "Şu modülü geliştir" → mevcut kodu oku, eksikleri gör, kapsamlı iyileştir

Sadece isteneni yapma — iyi bir yazılımcının yapacağını düşün.
Mevcut ZEKY mimarisiyle uyumlu ol. Gereksiz bağımlılık ekleme.

## ÇIKTI FORMATI

DOSYA: <proje_içi_yol>
```python
<kod>
```
AÇIKLAMA: <ne yaptın ve neden — kısa, net>"""

    SYSTEM_PROMPT_APPLY = f"""Sen ZEKY projesinin kıdemli Python geliştiricisisin.
{ZEKY_CONTEXT}

## ÇALIŞMA PRENSİBİN

Kullanıcı doğal dilde istek yazar. Niyeti anla, mevcut koda bak, ZEKY mimarisiyle uyumlu
tam çalışır kod üret. Eksik import, yanlış path, bozuk entegrasyon bırakma.

## ZORUNLU ÇIKTI FORMATI — Bu formattan sapma, dosyalar bu yapıya göre yazılacak:

DOSYA: src/grants/module.py
```python
# TAM dosya içeriği — snippet değil, deploy edilebilir hali
```
AÇIKLAMA: Ne değişti ve neden.

Her değiştirilen/oluşturulan dosya için ayrı DOSYA: bloğu yaz.
Dosya yolu proje köküne göre relative olmalı (src/... gibi)."""

    def run(self, task: str, context: Optional[Dict] = None) -> AgentResult:
        ctx = context or {}
        apply_mode = ctx.get("apply", False)
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

        apply_note = "\nÖNEMLİ: TAM dosya içeriğini yaz — snippet değil, deploy edilebilir hali." if apply_mode else ""
        prompt = f"""Proje: {self.project_path.name}

Mevcut kod:
{code_ctx}

İstek: {task}{apply_note}

Yukarıdaki ZEKY projesine göre bu isteği gerçekleştir."""

        system = self.SYSTEM_PROMPT_APPLY if apply_mode else self.SYSTEM_PROMPT

        try:
            output = self._ask(prompt, temperature=0.2, system_override=system)
            return AgentResult(
                agent="DevAgent",
                task=task,
                output=output,
                files_read=files_read,
            )
        except Exception as e:
            return AgentResult(agent="DevAgent", task=task, output="", error=str(e))
