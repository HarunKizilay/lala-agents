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

## ⚠️ KRİTİK KURAL — TAM DOSYA ZORUNLU

Bir dosyayı değiştiriyorsan:
- Tüm orijinal kodu koru, sadece gerekli satırları değiştir
- Snippet, "..." veya "# ... rest of code" YASAK — tam dosya yaz
- Dosya mevcut içerikten %30'dan az satırla tamamlanamaz
- Eğer dosya çok uzunsa (500+ satır) ve sadece küçük bir değişiklik gerekiyorsa:
  → O dosyaya hiç dokunma, sadece yeni/ek dosya yaz

## ZORUNLU ÇIKTI FORMATI — Her yanıt bu sırayı takip etmeli:

### 1. KULLANICI ÖZETİ (ÖNCE BU, teknik olmayan Türkçe)
📋 KULLANICI ÖZETİ
─────────────────────
İsteğiniz  : <kullanıcının ne istediği — 1 cümle>
Ne yaptım  : <ne değiştirdim/ekledim — teknik terim kullanmadan>
Ne değişir : <kullanıcı ZEKY'yi açtığında ne görecek/yapabilecek>
Risk       : <Yok | Düşük | Orta | Yüksek> — <varsa kısa açıklama>
Onaylayın mı: <✅ Evet, güvenle onaylayabilirsiniz | ⚠️ Dikkat: ...>

### 2. TEKNİK KOD (Sonra bu)
DOSYA: src/grants/module.py
```python
# TAM dosya içeriği — snippet değil, deploy edilebilir hali
# Orijinal kodu silme — sadece ekle/değiştir
```
AÇIKLAMA: Ne değişti ve neden.

Her değiştirilen/oluşturulan dosya için ayrı DOSYA: bloğu yaz.
Dosya yolu proje köküne göre relative olmalı (src/... gibi)."""

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

Mevcut kod:
{code_ctx}

İstek: {task}

Yukarıdaki ZEKY projesine göre bu isteği gerçekleştir."""

        system = self.SYSTEM_PROMPT_APPLY

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
