"""Engineering smoke test; not a scientific efficacy evaluation."""
from __future__ import annotations

import json
import time
from pathlib import Path

from collocagent.agents import CollocAgent

ROOT = Path(__file__).resolve().parents[1]
GOLD = ROOT / "data" / "pilot_gold.jsonl"
RULES = ROOT / "data" / "rules.json"
INDEX = ROOT / "data" / "collocagent.sqlite3"
OUT = ROOT / "artifacts" / "smoke_results.json"


def main() -> int:
    cases = [json.loads(line) for line in GOLD.read_text().splitlines() if line.strip()]
    agent = CollocAgent(RULES, INDEX)
    started = time.perf_counter()
    rows = []
    detection_ok = 0
    top1_ok = 0
    for case in cases:
        result = agent.analyze(case["text"])
        rules = [issue["rule_id"] for issue in result["issues"]]
        detected = case["expected_rule"] in rules
        recommended = None
        if detected:
            issue = next(i for i in result["issues"] if i["rule_id"] == case["expected_rule"])
            recommended = issue["recommended"]
        top_ok = recommended == case["expected_top"]
        detection_ok += int(detected)
        top1_ok += int(top_ok)
        rows.append({**case, "detected": detected, "recommended": recommended, "top1_ok": top_ok})
    elapsed_ms = (time.perf_counter() - started) * 1000
    summary = {
        "label": "engineering smoke test; constructed fixtures; not an external benchmark",
        "cases": len(cases),
        "expected_rule_detected": detection_ok,
        "expected_top_candidate": top1_ok,
        "elapsed_ms": round(elapsed_ms, 3),
        "rows": rows,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if detection_ok == len(cases) and top1_ok == len(cases) else 1


if __name__ == "__main__":
    raise SystemExit(main())
