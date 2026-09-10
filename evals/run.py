"""Run with python -m evals.run [--live] [--baseline previous-report.json]."""

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from time import perf_counter

from app.config import get_settings
from app.schemas import SegmentCustomer
from app.services.insights import (
    PROMPT_VERSION,
    SYSTEM,
    InsightsUnavailable,
    InvalidInsight,
    call_model,
    facts_for,
    validate_selection,
)

CASES_PATH = Path(__file__).with_name("cases.json")


def run(live: bool = False, repeats: int = 3) -> dict:
    if not 2 <= repeats <= 10:
        raise ValueError("repeats must be between 2 and 10")
    settings = get_settings()
    if live and (not settings.openai_api_key or not settings.insights_model):
        raise InsightsUnavailable("Configure OPENAI_API_KEY and INSIGHTS_MODEL")
    rows = []
    for case in json.loads(CASES_PATH.read_text()):
        facts = facts_for(
            SegmentCustomer(
                customer_id=case["id"],
                run_id=1,
                **{k: v for k, v in case.items() if k not in {"id", "expected"}},
            )
        )
        signatures, valid, useful, durations = [], 0, 0, []
        for _ in range(repeats):
            start = perf_counter()
            try:
                # Offline mode checks the harness only, NEVER claims model quality.
                raw = (
                    call_model(facts)
                    if live
                    else json.dumps(
                        {
                            "facts": facts,
                            "actions": [case["expected"]],
                        }
                    )
                )
                selected = validate_selection(raw, facts)
                valid += 1
                useful += selected.actions[0] == case["expected"]
                signatures.append(tuple(selected.actions))
            except (InvalidInsight, InsightsUnavailable):
                signatures.append(None)
            durations.append(perf_counter() - start)
        successful = [s for s in signatures if s is not None]
        agreement = Counter(successful).most_common(1)[0][1] / repeats if successful else 0
        rows.append(
            {
                "id": case["id"],
                "valid_rate": valid / repeats,
                "usefulness_proxy": useful / repeats,
                "consistency": agreement,
                "mean_latency_seconds": sum(durations) / repeats,
            }
        )
    return {
        "mode": "live" if live else "offline-harness-only",
        "repeats": repeats,
        "model": settings.insights_model if live else None,
        "prompt_version": PROMPT_VERSION,
        "prompt_sha256": hashlib.sha256(SYSTEM.encode()).hexdigest(),
        "cases_sha256": hashlib.sha256(CASES_PATH.read_bytes()).hexdigest(),
        "cases": rows,
    }


def regressions(report: dict, baseline: dict) -> list[str]:
    if any(report[key] != baseline[key] for key in ("mode", "cases_sha256", "repeats")):
        raise ValueError("Baseline must use the same mode, cases, and repeat count")
    previous = {case["id"]: case for case in baseline["cases"]}
    return [
        f"{case['id']}: {metric} decreased"
        for case in report["cases"]
        for metric in ("valid_rate", "usefulness_proxy", "consistency")
        if case[metric] < previous[case["id"]][metric]
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live", action="store_true", help="Makes paid API calls on synthetic data"
    )
    parser.add_argument("--repeats", type=int, default=3, choices=range(2, 11))
    parser.add_argument("--baseline", type=Path)
    args = parser.parse_args()
    try:
        report = run(args.live, args.repeats)
        report["regressions"] = (
            regressions(report, json.loads(args.baseline.read_text())) if args.baseline else []
        )
    except (InsightsUnavailable, ValueError, KeyError, OSError) as exc:
        parser.exit(2, f"Evaluation failed: {exc}\n")
    print(json.dumps(report, indent=2))
    failed = report["regressions"] or any(
        case[metric] < 1
        for case in report["cases"]
        for metric in ("valid_rate", "usefulness_proxy", "consistency")
    )
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
