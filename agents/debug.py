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
- Import hatası → src/ dizin yapısını kontrol et (WorkingDirectory=/root/ZEKY, sys.path.insert gerekir)
- SQLite bağlantı sorunu → context manager kullan
- Pandas dtype uyumsuzluğu → explicit cast ekle

## ⚠️ DOSYA DEĞİŞTİRME KURALI — KRİTİK

Eğer DOSYA: bloğu üretiyorsan (fix uygulanacak):
- Tam dosyayı yaz — sadece değişen satırı değil, TÜM dosya içeriğini
- "# ... existing code ..." veya snippet YASAK
- Dosyayı orijinal satır sayısından %70'den az satıra indirgeme
- Küçük bir fix (1-5 satır) için şunu yap:
  → Önce "DOSYA: path" bloğunda tüm dosyayı yaz
  → Ya da sadece AÇIKLAMA kısmında hangi satırı değiştirmesi gerektiğini söyle, DOSYA: bloğu yazma

## ÇIKTI FORMATI

📋 KULLANICI ÖZETİ
─────────────────────
Sorun    : <hata ne anlama geliyor — teknik terim kullanma>
Neden oldu: <bir cümle, sade dil>
Düzelttim : <ne değiştirdim>
Risk     : <Yok | Düşük | Orta>
Onaylayın mı: <✅ Evet | ⚠️ Dikkat: ...>

KÖK NEDEN: <bir cümle>
HATA YERİ: <dosya:satır>
DÜZELTİLMİŞ KOD:
```python
<düzeltme — tam dosya içeriği ile, snippet değil>
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
