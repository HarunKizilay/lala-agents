"""
Master Agent — Koordinatör.
Görevi analiz eder, uygun ajan(lar)a yönlendirir, sonuçları birleştirir.
Tüm projeler için çalışır; aktif proje config'den gelir.
"""
from __future__ import annotations

import json
from typing import Dict, List, Optional

from .base import BaseAgent, AgentResult
from .dev      import DevAgent
from .qa       import QAAgent
from .doc      import DocAgent
from .debug    import DebugAgent
from .security import SecurityAgent
from llm.client import ask


ROUTING_SYSTEM = """Sen bir yazılım proje koordinatörüsün.
Kullanıcının görevini analiz et ve hangi ajan(lar)ın çalışması gerektiğine karar ver.
Mevcut ajanlar:
- dev:      Kod yaz, özellik ekle, refactor et
- qa:       Test yaz, kod kalitesini değerlendir
- doc:      README, CHANGELOG, docstring yaz
- debug:    Hatayı bul ve düzelt
- security: Güvenlik açığı tara ve raporla
- all:      Tüm ajanları çalıştır (tam proje denetimi)

Yanıtın SADECE JSON olsun, başka hiçbir şey yazma:
{"agents": ["dev"], "reason": "neden bu ajan"}
veya
{"agents": ["dev", "qa"], "reason": "neden birden fazla"}"""


class MasterAgent(BaseAgent):

    ROLE = "master"
    SYSTEM_PROMPT = """Sen bir kıdemli yazılım mühendisi ve proje liderisisin.
Birden fazla ajan sonucunu alıp kapsamlı, uygulanabilir bir özet üretirsin.
Türkçe yaz. Teknik olmayan kısımları sade tut, kod kısımları net olsun."""

    def run(self, task: str, context: Optional[Dict] = None) -> AgentResult:
        ctx = context or {}

        # 1. Hangi ajanlar çalışacak?
        agents_to_run = ctx.get("agents") or self._route(task)

        # 2. Ajanları çalıştır
        results: List[AgentResult] = []
        all_files_read = []

        agent_map = {
            "dev":      DevAgent,
            "qa":       QAAgent,
            "doc":      DocAgent,
            "debug":    DebugAgent,
            "security": SecurityAgent,
        }

        if "all" in agents_to_run:
            agents_to_run = list(agent_map.keys())

        for agent_key in agents_to_run:
            cls = agent_map.get(agent_key)
            if not cls:
                continue
            agent = cls(str(self.project_path))
            result = agent.run(task, ctx)
            results.append(result)
            all_files_read.extend(result.files_read)

        # 3. Sonuçları birleştir
        if len(results) == 1:
            combined_output = results[0].output
        else:
            combined_output = self._synthesize(task, results)

        return AgentResult(
            agent="MasterAgent",
            task=task,
            output=combined_output,
            files_read=list(set(all_files_read)),
        )

    # ── yönlendirme ────────────────────────────────────────────────────────────

    def _route(self, task: str) -> List[str]:
        """LLM'e sorarak hangi ajanların çalışacağını belirler."""
        prompt = f"Görev: {task}\n\nHangi ajan(lar) bu görevi yapmalı?"
        try:
            raw = ask(prompt, system=ROUTING_SYSTEM, temperature=0.1)
            # JSON bul
            start = raw.find("{")
            end   = raw.rfind("}") + 1
            if start >= 0 and end > start:
                data = json.loads(raw[start:end])
                return data.get("agents", ["dev"])
        except Exception:
            pass
        return ["dev"]  # varsayılan

    def _synthesize(self, task: str, results: List[AgentResult]) -> str:
        """Birden fazla ajan çıktısını tek raporda birleştirir."""
        sections = "\n\n".join(
            f"=== {r.agent} ===\n{r.output}" for r in results if r.ok()
        )
        errors = [r for r in results if not r.ok()]

        prompt = f"""Görev: {task}

Ajanlardan gelen sonuçlar:
{sections}

Bu sonuçları bir araya getir:
1. Her ajanın önemli bulgularını koru
2. Çelişen önerileri belirt
3. Öncelikli aksiyon listesi yap (en kritikten başla)
4. Toplam değerlendirme yaz"""

        try:
            synthesis = ask(prompt, system=self.SYSTEM_PROMPT, temperature=0.3)
        except Exception as e:
            synthesis = sections + f"\n\n[Sentez başarısız: {e}]"

        if errors:
            err_section = "\n".join(f"- {r.agent}: {r.error}" for r in errors)
            synthesis += f"\n\nHATALI AJANLAR:\n{err_section}"

        return synthesis
