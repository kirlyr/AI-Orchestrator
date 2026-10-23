"""Conservative intent routing for the opt-in SmartCodex v2 path."""
from __future__ import annotations

import json
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .repo_analyzer import RepoSummary


@dataclass(frozen=True)
class Model:
    model: str
    effort: str
    requires_approval: bool = False


@dataclass(frozen=True)
class Profile:
    name: str
    tiers: dict[str, Model]
    classifier: Model
    fallback: Model
    fallback_approval: bool = True


@dataclass(frozen=True)
class IntentDecision:
    intent: str
    tier: str
    complexity: str
    scope_files: tuple[str, ...]
    risk: str
    confidence: float
    reason: str
    classifier_used: bool = False
    provisional: bool = False


def load_profile(path: str | Path, name: str = "testing") -> Profile:
    """Read the existing TOML without requiring tomllib on Python 3.10."""
    raw = Path(path).read_text(encoding="utf-8")
    try:
        import tomllib
        data = tomllib.loads(raw)
    except ModuleNotFoundError:
        try:
            import tomli
            data = tomli.loads(raw)
        except ModuleNotFoundError:
            # Parse just the scalar TOML subset used by the checked-in profile.
            data = {"profiles": {}}
            current = None
            for line in raw.splitlines():
                m = re.match(r"\[profiles\.([\w-]+)(?:\.([\w-]+)(?:\.([\w-]+))?)?\]", line.strip())
                if m:
                    p, group, tier = m.groups(); current = data["profiles"].setdefault(p, {})
                    if group: current = current.setdefault(group, {})
                    if tier: current = current.setdefault(tier, {})
                    continue
                m = re.match(r"([\w-]+)\s*=\s*(.+)", line.strip())
                if m and current is not None:
                    value = m.group(2).strip()
                    current[m.group(1)] = value.strip('"') if value.startswith('"') else value.lower() == "true" if value.lower() in ("true", "false") else int(value)
    config = data["profiles"][name]
    def model(section):
        return Model(section["model"], section["reasoning_effort"], bool(section.get("requires_approval", False)))
    return Profile(name, {k: model(v) for k, v in config["tiers"].items()}, model(config["classifier"]),
                   model(config["tiers"]["fallback"]), bool(config.get("require_approval_for_fallback", True)))


_RISK = re.compile(r"\b(?:database|migration|migrat|auth|authentication|authorization|permission|payment|security|production|deploy|delete|destroy|drop|purge|credential|secret)\w*\b", re.I)
_MULTI = re.compile(r"\b(?:across|multiple|several|end.to.end|full.stack|cross.module|lintas modul|beberapa modul|seluruh aplikasi|integrat\w*)\b", re.I)
_SMALL = re.compile(r"\b(?:typo|spelling|label|button text|teks tombol|ubah teks|rename|formatting|padding|margin|warna tombol|placeholder|comment|docstring)\b", re.I)


def repository_context(summary: RepoSummary) -> dict:
    return {"languages": list(summary.languages), "frameworks": list(summary.frameworks),
            "candidate_paths": list(summary.candidates[:12]), "file_count": len(summary.files),
            "truncated": summary.truncated}


def local_decision(prompt: str, summary: RepoSummary) -> IntentDecision | None:
    risk = bool(_RISK.search(prompt))
    multi = bool(_MULTI.search(prompt))
    small = bool(_SMALL.search(prompt))
    candidates = tuple(summary.candidates[:12])
    if risk:
        return IntentDecision("PLAN", "deep", "high", candidates, "high", .96,
                              "Area berisiko; perlu rencana dan pemeriksaan sebelum perubahan.")
    if multi:
        return IntentDecision("PLAN", "standard", "high", candidates, "medium", .91,
                              "Permintaan menunjukkan cakupan lintas modul/integrasi.")
    # Only direct when the request is explicit and repository candidates agree.
    if small and len(candidates) <= 3 and not summary.truncated:
        return IntentDecision("DIRECT", "simple", "low", candidates, "low", .91,
                              "Perubahan kecil, terlokalisasi, dan kandidat file terbatas.")
    return None


def classify(prompt: str, summary: RepoSummary, codex: str, profile: Profile, timeout: int = 120) -> IntentDecision:
    context = repository_context(summary)
    schema = {"type": "object", "properties": {"intent": {"enum": ["DIRECT", "PLAN"]}, "reason": {"type": "string"}},
              "required": ["intent", "reason"], "additionalProperties": False}
    instruction = ("Classify coding task only. Return JSON intent DIRECT or PLAN and short reason. Be conservative; ")
    instruction += "DIRECT only when one localized safe change. Context is metadata only.\nTASK:\n" + prompt[:7000] + "\nREPOSITORY SUMMARY:\n" + json.dumps(context)
    with tempfile.TemporaryDirectory(prefix="smartcodex-intent-") as temp:
        schema_path, output = Path(temp) / "schema.json", Path(temp) / "result.json"
        schema_path.write_text(json.dumps(schema), encoding="utf-8")
        cmd = [codex, "exec", "--ephemeral", "--skip-git-repo-check", "--sandbox", "read-only", "--model", profile.classifier.model,
               "-c", "model_reasoning_effort=" + profile.classifier.effort, "--output-schema", str(schema_path), "--output-last-message", str(output), "-"]
        result = subprocess.run(cmd, cwd=temp, input=instruction, text=True, capture_output=True, timeout=timeout, check=False)
        if result.returncode or not output.exists(): raise RuntimeError("Classifier tidak tersedia atau gagal.")
        answer = json.loads(output.read_text(encoding="utf-8"))
        intent = answer.get("intent")
        if intent not in ("DIRECT", "PLAN"): raise ValueError("Jawaban classifier tidak valid.")
        return IntentDecision(intent, "simple" if intent == "DIRECT" else "standard", "uncertain", tuple(context["candidate_paths"]),
                              "medium", .65, str(answer.get("reason", "Classifier Luna"))[:180], True)


def decide(prompt: str, summary: RepoSummary, codex: str | None, profile: Profile) -> IntentDecision:
    result = local_decision(prompt, summary)
    if result:
        return result
    if codex:
        try: return classify(prompt, summary, codex, profile)
        except Exception as exc:
            return IntentDecision("PLAN", "standard", "uncertain", tuple(summary.candidates[:12]), "medium", .35,
                                  "Classifier gagal; fallback konservatif ke PLAN (" + type(exc).__name__ + ").", False, True)
    return IntentDecision("PLAN", "standard", "uncertain", tuple(summary.candidates[:12]), "medium", .35,
                          "Classifier tidak tersedia; fallback konservatif ke PLAN.", False, True)
