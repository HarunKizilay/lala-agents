# LALA Ajan Sistemi

**6 ajan, tüm projeler için. Şu an öncelikli proje: ZEKY.**

---

## Mimari

```
Kullanıcı → main.py CLI
                ↓
          MasterAgent
          (görev analizi + yönlendirme)
                ↓
    ┌──────┬───────┬──────┬────────┬──────────┐
   Dev    QA    Doc   Debug   Security
    ↓      ↓     ↓      ↓        ↓
         [Her ajan LLM kullanır: Gemini → Claude]
                ↓
          MasterAgent (sonuçları birleştirir)
                ↓
          Rapor (konsol / Markdown / JSON)
```

Ajanlar **proje bağımsızdır** — `--project` ile herhangi bir klasöre yönlendirilebilir.  
Varsayılan proje: `C:/Users/aemre/Desktop/ZEKY`

---

## Ajanlar

### 1. Master Agent
**Rol:** Koordinatör  
**Ne yapar:** Görevi analiz eder, hangi ajan(lar)ın çalışacağına LLM ile karar verir, sonuçları birleştirir.  
**Ne zaman çalışır:** Her görevde; diğer ajanlar da doğrudan çağrılabilir.

### 2. Dev Agent
**Rol:** Kod geliştirici  
**Ne yapar:** Özellik ekler, refactor eder, mevcut mimariyle uyumlu kod yazar.  
**Çıktı:** Dosya yolu + kod bloğu + açıklama

### 3. QA Agent
**Rol:** Kalite güvence  
**Ne yapar:** Kodu inceler (mantık hatası, edge case, hata yönetimi), pytest testleri yazar.  
**Çıktı:** Kalite puanı (0-10) + bulgular + test kodu

### 4. Doc Agent
**Rol:** Teknik yazar  
**Ne yapar:** README, CHANGELOG, docstring üretir.  
**Çıktı:** Markdown dosyası içeriği

### 5. Debug Agent
**Rol:** Hata ayıklayıcı  
**Ne yapar:** Traceback + kodu analiz eder, kök nedeni bulur, düzeltilmiş kodu yazar.  
**Çıktı:** Kök neden + hata yeri + düzeltme kodu

### 6. Security Agent *(Yeni)*
**Rol:** Güvenlik denetçisi  
**Ne yapar:**
- Statik regex taraması (hardcoded credential, injection, eval, pickle, vs.)
- Bağımlılık denetimi (requirements.txt)
- LLM ile OWASP Top 10 analizi
**Çıktı:** Risk seviyesi + bulgular (KRİTİK/YÜKSEK/ORTA/DÜŞÜK) + aksiyon listesi

---

## Kullanım

```bash
cd C:\LALA\6_Agent_System

# Görev ver — Master ajan hangi ajanı çalıştıracağına karar verir
python main.py "analiz motoru için unit test yaz"

# Belirli ajan
python main.py security "tam güvenlik taraması yap"
python main.py dev "router.py'ye rate limiting ekle"
python main.py debug "login hatası" --error "AttributeError: 'NoneType' has no attribute 'username'"

# Farklı proje
python main.py security "güvenlik taraması" --project C:/Users/aemre/Documents/portfoy-takip

# Tüm ajanlar (tam denetim)
python main.py all "tam proje denetimi"

# Sonucu kaydet
python main.py security "güvenlik taraması yap" --save

# JSON çıktı
python main.py qa "kod kalitesini değerlendir" --json
```

---

## LLM

| Sıra | Sağlayıcı | Model | Not |
|------|-----------|-------|-----|
| 1. | LM Studio | localhost:1234 | Yerel, ücretsiz |
| 2. | OpenRouter | mistral-7b-instruct:free | Ücretsiz bulut |
| 3. | GitHub Models | gpt-4o-mini | GitHub PAT ile |
| 4. | Gemini | gemini-2.0-flash | Google API |
| 5. | Anthropic | claude-sonnet-4-6 | Son yedek |

API anahtarları `C:/Users/aemre/Desktop/ZEKY/.env` dosyasından okunur.

---

## Aktif Projeler

| Proje | Yol | Öncelik |
|-------|-----|---------|
| ZEKY | `C:/Users/aemre/Desktop/ZEKY` | 🔴 Yüksek (varsayılan) |
| Portföy Takip | `C:/Users/aemre/Documents/portfoy-takip` | 🟡 Beklemede |
| Farmakoloji Dersleri | `C:/Users/aemre/Documents/Farmakoloji_dersleri` | 🟡 Beklemede |

---

## Dosya Yapısı

```
6_Agent_System/
├── agents/
│   ├── __init__.py
│   ├── base.py         # BaseAgent, AgentResult
│   ├── master.py       # Koordinatör + yönlendirme
│   ├── dev.py          # Kod geliştirme
│   ├── qa.py           # Test + kalite
│   ├── doc.py          # Dokümantasyon
│   ├── debug.py        # Hata ayıklama
│   └── security.py     # Güvenlik denetimi
├── llm/
│   ├── __init__.py
│   └── client.py       # Gemini + Claude wrapper
├── logs/               # Kaydedilen çıktılar (--save)
├── main.py             # CLI giriş noktası
├── requirements.txt
├── .env.example
└── AGENTS.md           # Bu dosya
```

---

**Son güncelleme:** 29 Nisan 2026  
**Durum:** Aktif
