"""
LALA — Kod Validasyon Modülü

LLM çıktısı dosyaya yazılmadan önce burada doğrulanır:
- Python sözdizimi (AST parse)
- Tek satıra sıkışma tespiti (LLM'in yaygın hatası — kod tek satırda yazılmış olabilir)
- Yarım kod tespiti (ellipsis, "rest of code" gibi placeholder)
- Trivial dosya tespiti (sadece import veya çok kısa)
- Otomatik formatlama (black varsa)

Public API:
    validate_python_code(code, filepath) -> ValidationResult
    auto_fix(code) -> (fixed_code: str, was_fixed: bool)
"""
from __future__ import annotations

import ast
import re
import statistics
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


# ============ EŞİKLER ============

# Tek satıra sıkışma tespiti
MIN_LINES_FOR_LARGE_FILE = 5   # 200+ karakter ama 5'ten az satır = sıkışma şüphesi
MAX_AVG_LINE_LEN = 200          # ortalama satır uzunluğu bunu aşarsa şüphe
MAX_SINGLE_LINE_LEN = 500       # tek bir satırın bu kadar uzun olması = sıkışma

# Yasak placeholder pattern'ları
PLACEHOLDER_PATTERNS = [
    re.compile(r"#\s*\.{3,}\s*rest of code", re.I),
    re.compile(r"#\s*\.{3,}\s*remaining code", re.I),
    re.compile(r"#\s*\.{3,}\s*existing code", re.I),
    re.compile(r"#\s*\.{3,}\s*previous code", re.I),
    re.compile(r"#\s*TODO:\s*kalan kısım", re.I),
    re.compile(r"#\s*\.{3,}\s*kalanı aynı", re.I),
    re.compile(r"^\s*\.{3,}\s*$", re.M),  # tek başına ... satırı
]


@dataclass
class ValidationResult:
    """Bir Python dosyasının validasyon sonucu."""
    ok: bool = True
    filepath: str = ""
    errors: List[str] = field(default_factory=list)      # ENGEL — yazma reddedilir
    warnings: List[str] = field(default_factory=list)    # UYARI — yazılır ama bildir

    line_count: int = 0
    char_count: int = 0
    avg_line_len: float = 0.0
    longest_line_len: int = 0

    auto_fixed: bool = False
    fixed_code: Optional[str] = None  # auto_fix uygulandıysa düzeltilmiş kod

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)
        self.ok = False

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)

    def summary(self) -> str:
        """Kullanıcı/log için kısa özet."""
        if self.ok and not self.warnings:
            return f"✅ `{self.filepath}` ({self.line_count} satır) — temiz"
        parts = []
        for e in self.errors:
            parts.append(f"🔴 {e}")
        for w in self.warnings:
            parts.append(f"🟡 {w}")
        prefix = "✅" if self.ok else "❌"
        return f"{prefix} `{self.filepath}` ({self.line_count} satır)\n  " + "\n  ".join(parts)


# ============ ANA VALİDASYON ============

def validate_python_code(code: str, filepath: str = "<unknown>") -> ValidationResult:
    """
    Bir Python kod stringini validate eder.
    Sadece .py dosyaları için kullanılmalı (.md, .json vb. için kullanma).
    """
    result = ValidationResult(filepath=filepath)

    # Boş/whitespace kontrolü
    if not code or not code.strip():
        result.add_error("Boş kod — LLM hiçbir içerik üretmemiş")
        return result

    # Temel istatistikler
    lines = code.splitlines()
    result.line_count = len(lines)
    result.char_count = len(code)
    line_lens = [len(line) for line in lines if line.strip()]
    result.avg_line_len = statistics.mean(line_lens) if line_lens else 0
    result.longest_line_len = max(line_lens) if line_lens else 0

    # ── 1. TEK SATIRA SIKIŞMA TESPİTİ ──
    # 50+ karakterlik dosya ve 3'ten az satır = direkt sıkışma
    if result.char_count > 50 and result.line_count < 3:
        result.add_error(
            f"Tek satıra sıkışmış — {result.char_count} karakter ama sadece "
            f"{result.line_count} satır var. LLM yeni satır karakterlerini eklemedi."
        )
        return result

    if result.char_count > 200 and result.line_count < MIN_LINES_FOR_LARGE_FILE:
        result.add_error(
            f"Tek satıra sıkışmış — {result.char_count} karakter ama sadece "
            f"{result.line_count} satır var."
        )
        return result

    if result.avg_line_len > MAX_AVG_LINE_LEN:
        result.add_error(
            f"Ortalama satır uzunluğu çok yüksek ({result.avg_line_len:.0f} karakter) — "
            f"kod muhtemelen tek satıra sıkıştırılmış."
        )

    if result.longest_line_len > MAX_SINGLE_LINE_LEN:
        result.add_error(
            f"En uzun satır {result.longest_line_len} karakter — bir satıra fazla statement "
            f"sıkıştırılmış olabilir (semicolon zincirleri vb.)."
        )

    # ── 2. SEMICOLON İSTİSMARI ──
    # Tek satırda 3+ semicolon = direkt sıkışma
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith('"') or stripped.startswith("'"):
            continue
        # String içindeki ; saymıyoruz — basit bir yaklaşım: kod kısmını ayır
        code_part = stripped.split("#")[0]
        if code_part.count(";") >= 3:
            result.add_error(
                f"Satır {i}: tek satırda {code_part.count(';')} semicolon — "
                f"'a; b; c' formatında statement zinciri var, ayrı satırlara bölünmeli."
            )
            break

    # 3+ satırda 2+ semicolon = yine sıkışma şüphesi
    semicolon_lines = [
        i for i, line in enumerate(lines, 1)
        if line.split("#")[0].count(";") >= 2 and not line.strip().startswith("#")
    ]
    if len(semicolon_lines) >= 3:
        result.add_error(
            f"Çok fazla semicolon zinciri ({len(semicolon_lines)} satırda 2+ semicolon) — "
            f"LLM 'a; b; c' formatında yazıyor, ayrı satırlara bölmeli."
        )

    # ── 3. PLACEHOLDER TESPİTİ ──
    for pattern in PLACEHOLDER_PATTERNS:
        if pattern.search(code):
            result.add_error(
                f"Placeholder bulundu (pattern: {pattern.pattern[:50]}) — "
                f"LLM tam kod üretmemiş, '... rest of code' bırakmış."
            )
            return result

    # ── 4. AST PARSE (Python sözdizimi geçerli mi?) ──
    if filepath.endswith(".py"):
        try:
            ast.parse(code)
        except SyntaxError as e:
            result.add_error(
                f"Python sözdizim hatası: satır {e.lineno}, kolon {e.offset} — {e.msg}"
            )
            return result

    # ── 5. Trivial dosya tespiti (sadece import + pass vb.) ──
    non_empty = [l for l in lines if l.strip() and not l.strip().startswith("#")]
    if len(non_empty) < 3 and result.char_count > 100:
        result.add_warning(
            f"Çok az anlamlı satır ({len(non_empty)}) ama dosya {result.char_count} karakter — şüpheli."
        )

    return result


# ============ OTOMATİK DÜZELTME ============

def auto_fix(code: str) -> Tuple[str, bool]:
    """
    Python kodunu black ile yeniden formatlar (varsa).
    Returns: (fixed_code, was_fixed)
    """
    try:
        import black
    except ImportError:
        return code, False

    try:
        mode = black.Mode(line_length=100)
        fixed = black.format_str(code, mode=mode)
        return fixed, fixed != code
    except Exception:
        # black parse edemediyse zaten kod bozuk demektir
        return code, False


def validate_and_fix(code: str, filepath: str = "<unknown>") -> ValidationResult:
    """
    Önce validate eder, eğer fix edilebilir bir hata varsa black ile düzeltmeyi dener,
    sonra tekrar validate eder.
    """
    result = validate_python_code(code, filepath)

    if not result.ok and filepath.endswith(".py"):
        # AST hatasız ama formatı kötüyse black ile düzelt
        try:
            ast.parse(code)
            fixed_code, was_fixed = auto_fix(code)
            if was_fixed:
                fixed_result = validate_python_code(fixed_code, filepath)
                if fixed_result.ok:
                    fixed_result.auto_fixed = True
                    fixed_result.fixed_code = fixed_code
                    fixed_result.add_warning(
                        "Kod tek satıra sıkıştırılmış olduğu için black ile yeniden formatlandı."
                    )
                    return fixed_result
        except SyntaxError:
            pass

    return result


# ============ PROMPT İÇİN HATA AÇIKLAMASI ============

def errors_to_revision_prompt(results: List[ValidationResult]) -> str:
    """
    Validasyon hatalarını LLM'e geri verilecek bir revizyon prompt'una çevirir.
    Otomatik retry için kullanılır.
    """
    bad_files = [r for r in results if not r.ok]
    if not bad_files:
        return ""

    msg = "Önceki yanıtınız aşağıdaki hatalarla reddedildi. **Lütfen tekrar yazın:**\n\n"
    for r in bad_files:
        msg += f"### `{r.filepath}` ({r.line_count} satır, {r.char_count} karakter)\n"
        for e in r.errors:
            msg += f"- ❌ {e}\n"
        msg += "\n"

    msg += (
        "\n**KRİTİK KURALLAR (Bu sefer mutlaka uyun):**\n"
        "1. Her Python statement KENDI SATIRINDA olmalı.\n"
        "2. ASLA `a; b; c` gibi semicolon ile statement zincirleme YAZMAYIN.\n"
        "3. ASLA `# ... rest of code` gibi placeholder bırakmayın — tam kodu yazın.\n"
        "4. Her import ayrı satırda: `import os` ve `import sys` ayrı satırlar.\n"
        "5. Fonksiyon gövdesi 4 boşluk girintiyle, yeni satırda başlar.\n"
        "6. Markdown code block içinde gerçek satır sonu karakterleri kullanın (\\n).\n\n"
        "## YANLIŞ:\n"
        "```python\n"
        "def f(x): a = x + 1; b = a * 2; return b\n"
        "```\n\n"
        "## DOĞRU:\n"
        "```python\n"
        "def f(x):\n"
        "    a = x + 1\n"
        "    b = a * 2\n"
        "    return b\n"
        "```\n"
    )
    return msg
