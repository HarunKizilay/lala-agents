"""
Master Agent — Koordinatör.
Görevi analiz eder, uygun ajan(lar)ı çalıştırır, sonuçları sentezler.
LLM ile routing yapmaz — kural tabanlı, hızlı, güvenilir.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from .base import BaseAgent, AgentResult, ZEKY_CONTEXT
from .dev      import DevAgent
from .qa       import QAAgent
from .doc      import DocAgent
from .debug    import DebugAgent
from .security import SecurityAgent
from llm.client import ask


AGENT_MAP = {
    "dev":      DevAgent,
    "qa":       QAAgent,
    "doc":      DocAgent,
    "debug":    DebugAgent,
    "security": SecurityAgent,
}

SYNTHESIZE_SYSTEM = f"""Sen ZEKY projesinin kıdemli koordinatörüsün.
{ZEKY_CONTEXT}

Birden fazla uzman ajanın çıktısını alıp kapsamlı, uygulanabilir bir özet üretirsin.
Türkçe yaz. En kritik bulgulardan başla. Çelişen önerileri belirt.
Aksiyon listesini net ve öncelik sıralı ver."""


class MasterAgent(BaseAgent):

    ROLE = "master"
    SYSTEM_PROMPT = SYNTHESIZE_SYSTEM

    def run(self, task: str, context: Optional[Dict] = None) -> AgentResult:
        ctx = context or {}

        agents_to_run = ctx.get("agents") or self._smart_route(task)

        if "all" in agents_to_run:
            agents_to_run = list(AGENT_MAP.keys())

        results: List[AgentResult] = []
        all_files_read = []

        for agent_key in agents_to_run:
            cls = AGENT_MAP.get(agent_key)
            if not cls:
                continue
            result = cls(str(self.project_path)).run(task, ctx)
            results.append(result)
            all_files_read.extend(result.files_read)

        combined_output = (
            results[0].output if len(results) == 1
            else self._synthesize(task, results)
        )

        return AgentResult(
            agent="MasterAgent",
            task=task,
            output=combined_output,
            files_read=list(set(all_files_read)),
        )

    # ── kural tabanlı yönlendirme (LLM çağrısı yok) ──────────────────────────

    def _smart_route(self, task: str) -> List[str]:
        t = task.lower()

        if any(w in t for w in ["güvenlik", "security", "açık", "zafiyet", "owasp", "inject"]):
            return ["security"]

        if any(w in t for w in ["hata", "bug", "çalışmıyor", "patlıyor", "traceback", "error", "fix"]):
            return ["debug", "qa"]

        if any(w in t for w in ["test", "pytest", "kapsam", "coverage"]):
            return ["qa"]

        if any(w in t for w in ["denetle", "tara", "incele", "review", "tümünü", "hepsini"]):
            return ["qa", "security"]

        if any(w in t for w in ["readme", "changelog", "docstring", "belge", "dokümantasyon", "belgele"]):
            return ["doc"]

        # Varsayılan: geliştirme
        return ["dev"]

    # ── sentez ────────────────────────────────────────────────────────────────

    def _synthesize(self, task: str, results: List[AgentResult]) -> str:
        sections = "\n\n".join(
            f"=== {r.agent} ===\n{r.output}" for r in results if r.ok()
        )
        errors = [r for r in results if not r.ok()]

        prompt = f"""Görev: {task}

Uzman ajan sonuçları:
{sections}

Bu sonuçları birleştir:
1. Her ajanın kritik bulgularını koru
2. Çelişen önerileri belirt
3. Öncelikli aksiyon listesi yap (en kritikten başla)
4. Kısa genel değerlendirme yaz"""

        try:
            synthesis = ask(prompt, system=self.SYSTEM_PROMPT, temperature=0.3)
        except Exception as e:
            synthesis = sections + f"\n\n[Sentez başarısız: {e}]"

        if errors:
            err_section = "\n".join(f"- {r.agent}: {r.error}" for r in errors)
            synthesis += f"\n\nHATALI AJANLAR:\n{err_section}"

        return synthesis
