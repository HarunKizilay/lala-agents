"""Security Agent — Güvenlik açığı tespiti, OWASP, bağımlılık denetimi."""
from __future__ import annotations
import re
from typing import Dict, List, Optional
from .base import BaseAgent, AgentResult


# Statik tarama: regex tabanlı hızlı kontroller
STATIC_RULES = [
    (r"eval\s*\(",          "KRİTİK", "eval() kullanımı — kod injection riski"),
    (r"exec\s*\(",          "KRİTİK", "exec() kullanımı — kod injection riski"),
    (r"os\.system\s*\(",    "KRİTİK", "os.system() — komut injection riski"),
    (r"subprocess.*shell\s*=\s*True", "KRİTİK", "shell=True — komut injection riski"),
    (r"pickle\.loads?\s*\(","YÜKSEK",  "pickle.load() — güvensiz deserializasyon"),
    (r"password\s*=\s*['\"][^'\"]+['\"]", "YÜKSEK", "Hardcoded şifre tespit edildi"),
    (r"secret\s*=\s*['\"][^'\"]+['\"]",   "YÜKSEK", "Hardcoded secret tespit edildi"),
    (r"api_key\s*=\s*['\"][^'\"]+['\"]",  "YÜKSEK", "Hardcoded API anahtarı"),
    (r"\.format\(.*request\.", "ORTA", "str.format() + request verisi — injection riski"),
    (r"f['\"].*{.*request\.", "ORTA",   "f-string + request verisi — injection riski"),
    (r"DEBUG\s*=\s*True",    "ORTA",   "DEBUG=True production'da tehlikeli"),
    (r"verify\s*=\s*False",  "ORTA",   "SSL doğrulama devre dışı (verify=False)"),
    (r"http://",             "DÜŞÜK",  "HTTP kullanımı — HTTPS tercih edilmeli"),
    (r"random\.",            "DÜŞÜK",  "random modülü — kriptografik amaç için secrets kullan"),
    (r"md5|sha1\b",          "DÜŞÜK",  "Zayıf hash algoritması (md5/sha1)"),
]


class SecurityAgent(BaseAgent):

    ROLE = "security"
    SYSTEM_PROMPT = """Sen ZEKY projesinin güvenlik uzmanısın.
Görevin: kodu OWASP Top 10 ve Python güvenlik pratiklerine göre denetlemek.

Her yanıtını şu formatta ver:

📋 KULLANICI ÖZETİ
─────────────────────
Güvenlik durumu : <Güvenli | Dikkat gerektiriyor | Kritik sorun var>
Kullanıcıya etkisi: <sorun varsa ne olabilir — teknik terim kullanma>
Acil aksiyon    : <gerekiyorsa ne yapılmalı, gerekmiyorsa "Yok">

GENEL RİSK: KRİTİK | YÜKSEK | ORTA | DÜŞÜK | GÜVENLİ
BULGULAR:
- [SEVİYE] dosya:satır — açıklama + düzeltme önerisi
ÖNCELİKLİ AKSİYONLAR:
1. <en acil düzeltme>"""

    def run(self, task: str, context: Optional[Dict] = None) -> AgentResult:
        ctx = context or {}
        files_read = []

        # 1. Statik regex taraması
        static_findings = self._static_scan()

        # 2. Bağımlılık kontrolü
        dep_findings = self._check_dependencies()

        # 3. LLM derin analizi
        if "files" in ctx:
            code_ctx = self._build_code_context(
                {f: self.read_file(f) for f in ctx["files"]}
            )
            files_read = ctx["files"]
        else:
            py_files = self.read_files("**/*.py")
            code_ctx = self._build_code_context(py_files)
            files_read = list(py_files.keys())

        static_section = self._format_static(static_findings)
        dep_section = "\n".join(dep_findings) if dep_findings else "Bağımlılık dosyası bulunamadı."

        prompt = f"""Proje: {self.project_path.name}

OTOMATİK TARAMA BULGULARI (regex):
{static_section}

BAĞIMLILIK KONTROL NOTLARI:
{dep_section}

KOD:
{code_ctx}

Güvenlik görevi: {task}

Yukarıdaki otomatik bulgulara ek olarak kodu derin güvenlik analizi yap."""

        try:
            llm_output = self._ask(prompt, temperature=0.1)
            combined = f"=== OTOMATİK TARAMA ===\n{static_section}\n\n=== LLM ANALİZİ ===\n{llm_output}"
            return AgentResult(
                agent="SecurityAgent",
                task=task,
                output=combined,
                files_read=files_read,
            )
        except Exception as e:
            # LLM başarısız olsa bile statik tarama sonucunu döndür
            fallback = f"LLM analizi başarısız: {e}\n\n=== OTOMATİK TARAMA ===\n{static_section}"
            return AgentResult(agent="SecurityAgent", task=task, output=fallback, files_read=files_read)

    # ── yardımcı metodlar ─────────────────────────────────────────────────────

    def _static_scan(self) -> List[Dict]:
        """Tüm Python dosyalarını regex ile tarar."""
        findings = []
        for rel_path in self.list_files("**/*.py"):
            content = self.read_file(rel_path)
            for pattern, severity, description in STATIC_RULES:
                for match in re.finditer(pattern, content, re.IGNORECASE):
                    line_no = content[:match.start()].count("\n") + 1
                    findings.append({
                        "severity":    severity,
                        "file":        rel_path,
                        "line":        line_no,
                        "description": description,
                        "snippet":     match.group()[:80],
                    })
        return findings

    def _check_dependencies(self) -> List[str]:
        """requirements.txt içindeki şüpheli veya eski paketleri kontrol eder."""
        req_file = self.project_path / "requirements.txt"
        if not req_file.exists():
            return []
        notes = []
        content = req_file.read_text(encoding="utf-8", errors="ignore")
        # Bilinen riskli paketler
        risky = {
            "pyyaml": "yaml.load() güvensiz — yaml.safe_load() kullan",
            "pickle":  "pickle doğrudan bağımlılık — güvensiz deserializasyon",
            "requests": "verify=False kullanıldığında SSL riski",
        }
        for pkg, note in risky.items():
            if pkg in content.lower():
                notes.append(f"[UYARI] {pkg}: {note}")
        notes.append(f"Toplam {len(content.splitlines())} bağımlılık satırı var.")
        return notes

    def _format_static(self, findings: List[Dict]) -> str:
        if not findings:
            return "Otomatik taramada bulgu bulunamadı."
        by_severity = {"KRİTİK": [], "YÜKSEK": [], "ORTA": [], "DÜŞÜK": []}
        for f in findings:
            by_severity.get(f["severity"], by_severity["DÜŞÜK"]).append(f)
        lines = []
        for sev in ["KRİTİK", "YÜKSEK", "ORTA", "DÜŞÜK"]:
            for f in by_severity[sev]:
                lines.append(
                    f"[{sev}] {f['file']}:{f['line']} — {f['description']}"
                    f"\n  snippet: {f['snippet']}"
                )
        return "\n".join(lines) if lines else "Bulgu yok."
