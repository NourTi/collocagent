"""Three-stage standalone CollocAgent pipeline."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .corpus import CorpusIndex


@dataclass(frozen=True)
class Finding:
    rule_id: str
    original: str
    start: int
    end: int
    relation: str
    severity: str
    rationale: str
    candidates: tuple[dict[str, str], ...]


class DiagnosticAgent:
    """Detects only explicitly declared learner-error patterns.

    This conservative design privileges precision: unsupported phrases are not
    silently classified as errors.
    """

    def __init__(self, rules: list[dict[str, Any]]):
        self.rules = rules

    def inspect(self, text: str) -> list[Finding]:
        findings: list[Finding] = []
        for rule in self.rules:
            for pattern in rule["patterns"]:
                rx = re.compile(rf"\b{re.escape(pattern)}\b", re.IGNORECASE)
                for match in rx.finditer(text):
                    findings.append(
                        Finding(
                            rule_id=rule["id"],
                            original=match.group(0),
                            start=match.start(),
                            end=match.end(),
                            relation=rule["relation"],
                            severity=rule.get("severity", "recommendation"),
                            rationale=rule["rationale"],
                            candidates=tuple(rule["candidates"]),
                        )
                    )
        return sorted(findings, key=lambda f: (f.start, f.end, f.rule_id))


class RetrievalAgent:
    """Ranks declared candidates using reproducible corpus evidence."""

    def __init__(self, corpus: CorpusIndex):
        self.corpus = corpus

    def rank(self, finding: Finding) -> list[dict[str, Any]]:
        ranked: list[dict[str, Any]] = []
        for prior_rank, candidate in enumerate(finding.candidates):
            evidence = self.corpus.association(candidate["collocate"], candidate["base"])
            concordances = self.corpus.concordances(
                candidate["collocate"], candidate["base"], limit=2
            )
            ranked.append(
                {
                    "phrase": candidate["phrase"],
                    "collocate": candidate["collocate"],
                    "base": candidate["base"],
                    "prior_rank": prior_rank,
                    "evidence": evidence,
                    "concordances": concordances,
                }
            )
        ranked.sort(
            key=lambda item: (
                item["evidence"]["pair_count"] > 0,
                item["evidence"]["pair_count"],
                item["evidence"]["log_dice"]
                if item["evidence"]["log_dice"] is not None
                else float("-inf"),
                -item["prior_rank"],
            ),
            reverse=True,
        )
        return ranked


class ExplanationAgent:
    """Produces templated, evidence-bounded feedback without invented counts."""

    def explain(self, finding: Finding, ranked: list[dict[str, Any]], corpus_meta: dict) -> dict:
        best = ranked[0]
        pair_count = best["evidence"]["pair_count"]
        if pair_count > 0:
            evidence_status = "attested_in_indexed_corpus"
            evidence_summary = (
                f"The recommended pair occurs {pair_count} time(s) in the indexed corpus; "
                f"log-Dice={best['evidence']['log_dice']}."
            )
        else:
            evidence_status = "insufficient_corpus_evidence"
            evidence_summary = (
                "The indexed corpus contains no occurrence of the recommended pair. "
                "The rule-based recommendation is shown, but no corpus-strength claim is made."
            )
        return {
            "rule_id": finding.rule_id,
            "span": {
                "text": finding.original,
                "start": finding.start,
                "end": finding.end,
            },
            "relation": finding.relation,
            "severity": finding.severity,
            "recommended": best["phrase"],
            "alternatives": [item["phrase"] for item in ranked[1:3]],
            "rationale": finding.rationale,
            "evidence_status": evidence_status,
            "evidence_summary": evidence_summary,
            "corpus": {
                "name": corpus_meta.get("corpus_name"),
                "fingerprint_sha256": corpus_meta.get("fingerprint_sha256"),
                "window": corpus_meta.get("window"),
            },
            "statistics": best["evidence"],
            "concordances": best["concordances"],
            "candidate_ranking": ranked,
        }


class CollocAgent:
    """Orchestrates diagnostic, retrieval, and explanation stages."""

    def __init__(self, rules_path: str | Path, index_path: str | Path):
        self.rules_path = Path(rules_path)
        self.index = CorpusIndex(index_path)
        rules = json.loads(self.rules_path.read_text(encoding="utf-8"))
        self.diagnostic = DiagnosticAgent(rules)
        self.retrieval = RetrievalAgent(self.index)
        self.explanation = ExplanationAgent()

    def analyze(self, text: str) -> dict[str, Any]:
        if not text or not text.strip():
            raise ValueError("text must not be empty")
        meta = self.index.metadata()
        if meta.get("status") != "ready":
            raise RuntimeError("Corpus index is missing. Build it before analysis.")
        findings = self.diagnostic.inspect(text)
        issues = []
        for finding in findings:
            ranked = self.retrieval.rank(finding)
            issues.append(self.explanation.explain(finding, ranked, meta))
        return {
            "system": "CollocAgent",
            "version": "0.1.0",
            "input": text,
            "issue_count": len(issues),
            "issues": issues,
            "provenance": {
                "rules_file": self.rules_path.name,
                "corpus": meta,
                "claim_policy": (
                    "Counts and concordances are emitted only when retrieved from the "
                    "indexed corpus; otherwise the system reports insufficient evidence."
                ),
            },
        }
