# LALA – Harun Kızılay'ın İkinci Beyni

## Profil

Harun Kızılay, 55 yaşında. Eczacı (1992), Farmakoloji doktoru.
- 1997-2019: Serbest eczacı
- 2001-2009: Eczacı Odası yönetim kurulu, başkanlık
- 2009-2017: Türk Eczacıları Birliği merkez heyeti, 2. başkan, 6 yıl genel sekreter
- 2019-2020: TİTCK başkan yardımcısı, 2 ay başkanlık
- 2022–: Selçuk Üniversitesi Eczacılık Fakültesi, Farmakoloji ABD başkanı, Dr. öğretim üyesi

İngilizce B1. Anadolu Üniversitesi Açık Öğretim Bilgisayar Programcılığı önlisans öğrencisi (3 ders kaldı). VS Code ile Python öğreniyor. ML ve ANN'e ilgi duyuyor.

## Ana Hedefler

1. Doçentlik: SCIE indeksli bir yayında ilk isim
2. Programlama: Önlisansı bitir + Python/ML/ANN öğren
3. Akademik çalışmalar: Farmakoloji araştırmaları ve yayınlar
4. Eğitim: Öğrenciler için materyal hazırlama
5. Kişisel: Portföy yönetimi, dil öğrenimi

## Kurallar

1. RAW/ klasörüne dokunma – sadece oku
2. Hiçbir dosya silme – yanlışsa _arşiv/ klasörüne taşı
3. Her önemli iş log.md'ye yaz: `## [YYYY-MM-DD] işlem | açıklama`
4. Türkçe cevap ver, teknik terimleri olduğu gibi bırak
5. Emin değilsen sor

## LALA Sistemi – Bilgisayar Yapısı

### Ana Bilgisayarlar
- **Ev bilgisayarı:** C:\LALA (Google Drive symlink → G:\Drive'ım\Harun\LALA)
- **Okul bilgisayarı:** C:\LALA (Google Drive symlink)
- **Laptop:** C:\LALA (Google Drive yok, lala-agents git repo tabanlı senkronizasyon)

### Laptop Notları
- Google Drive yok; CLAUDE.md ve aktif.md lala-agents reposunda, git ile senkronize
- ZEKY ve lala-agents repoları: C:\LALA\ZEKY ve C:\LALA\lala-agents
- SSH key: ~/.ssh/id_ed25519 (GitHub + DO eklendi)
- `.env` dosyaları kuruldu: `C:\LALA\lala-agents\.env` ve `C:\LALA\ZEKY\.env` (tüm API keyleri dolu)
- Telegram Chat ID: 1447186368
- Claude Code → Anthropic direkt (`C:\Users\Lenovo\.claude\settings.json`)

## LALA Agent Sistemi – Mevcut Durum (25 Nisan 2026)

### Altyapı

- **6 Ajan:** Master, Dev, QA, Doc, Debug, Security
- **LLM Zinciri:** LM Studio (Tailscale 100.109.228.17:1234) → OpenRouter → GitHub Models → Gemini → Anthropic
- **LM Studio Modeli:** `google/gemma-4-e4b`
- **Telegram Bot:** DO'da systemd servisi olarak 7/24 çalışıyor (`lala-bot.service`)
- **Varsayılan Proje:** `/root/ZEKY` (DO), `C:/Users/aemre/Desktop/ZEKY` (okul), `C:/LALA/ZEKY` (laptop)
- **LM Studio:** Okul bilgisayarında, Windows başlangıcında otomatik açılıyor, uyku modu kapalı

### Telegram Kullanımı – Doğal Dil

Bot artık slash komut gerektirmiyor. **Ne istediğini Türkçe yaz, sistem otomatik yönlendirir.**

```
Grants modülü ekle, hibe başvuru formu olsun
_home_ui.py 158. satırda hata var, düzelt
Analiz Motorunu belgele
ZEKY projesini güvenlik açısından tara
```

Ajan cevap verince 4 buton çıkar:
- ✅ Uygula → dosyalara yazar, push yapmaz
- ✅ Uygula + Push → yazar + GitHub push + DO deploy
- ✏️ Revize Et → ajanla yazışarak değişiklik iste
- ❌ İptal

Slash komutlar hâlâ çalışır (isteğe bağlı):
```
/durum   → Bot durumu ve kullanım rehberi
/iptal   → Bekleyen işlemi iptal et
```

### Ajan Özellikleri

- **Tüm ajanlar** ZEKY projesini ve kullanıcı profilini bilir (ZEKY_CONTEXT)
- **Tüm ajanlar** teknik olmayan Türkçe özet üretir (KULLANICI ÖZETİ formatı)
- **Dev ajanı** daima tam dosya yazar (snippet değil)
- **Master ajan** keyword tabanlı yönlendirme yapar (LLM harcamaz)
- **Otomatik güvenlik kapısı** kod uygulanmadan önce tarar; kritik bulgu varsa push engellenir

### Tam Otomasyon Döngüsü

```
Telegram mesajı → LALA Bot (DO 7/24) → Ajan + LLM → Önce KULLANICI ÖZETİ
→ Güvenlik taraması → Butonlar → Sen onaylarsın
→ Dosya yazılır → GitHub push → GitHub Actions → DO deploy → ZEKY canlıya geçer
```

### Dosyalar

- `lala-agents/telegram_bot.py` → Ana bot
- `lala-agents/llm/client.py` → LLM zinciri
- `lala-agents/agents/` → 6 ajan
- `lala-agents/main.py` → CLI + apply/push mantığı
- `/etc/systemd/system/lala-bot.service` → DO servis dosyası

### Sunucu Bilgileri

- **DO IP:** 165.245.213.201
- **ZEKY servisi:** `zeky.service` → `/root/ZEKY`, port 8501
- **LALA Bot servisi:** `lala-bot.service` → `/root/LALA`
- **GitHub Repos:** HarunKizilay/ZEKY · HarunKizilay/lala-agents
- **Tailscale:** Okul PC → 100.109.228.17 | DO → 100.77.111.6

## ZEKY Ajan Görev Listesi

**Eksik Modüller:**
- `Grants modülü ekle, hibe ve proje başvuru asistanı olsun`
- `Research Types modülü ekle, araştırma tipi sınıflandırma sistemi yap`

**İyileştirme:**
- `Seminer modülündeki SMTP e-posta gönderimi çalışıyor mu kontrol et`
- `ZEKY API dokümantasyonu oluştur`
