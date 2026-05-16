"""Eval runner for the LinkedIn wedge writer.

Execution model:
  1. Load seeds.json.
  2. For each seed, invoke the Writer agent directly with the seed's
     pre-built commander/scout/thinker outputs (upstream agents are held
     constant so the eval isolates Writer voice quality).
  3. Feed each draft to the LLM judge and collect structured scores.
  4. Write a timestamped report to reports/ and a stable report.json symlink
     target.
  5. Compare aggregate scores to baseline.json (if present). Exit non-zero
     on regression beyond the allowed deltas.

Invoke:
  cd backend && python -m tests.evals.runner
  cd backend && python -m tests.evals.runner --update-baseline

Required env:
  ANTHROPIC_API_KEY — real key, no placeholder. Missing key fails loudly.

The runner explicitly refuses to silently fall back to mock content; any
failure in the Writer path is surfaced as a run-level error.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Ensure backend/ is on sys.path whether invoked as module or script.
EVALS_DIR = Path(__file__).resolve().parent
BACKEND_DIR = EVALS_DIR.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from agents.writer import run_writer  # noqa: E402
from services.llm_keys import anthropic_available, strip_valid_key  # noqa: E402

from .judge import JudgeError, JudgeScore, score_draft  # noqa: E402

logger = logging.getLogger("evals.runner")

SEEDS_PATH = EVALS_DIR / "seeds.json"
BASELINE_PATH = EVALS_DIR / "baseline.json"
REPORTS_DIR = EVALS_DIR / "reports"

# Allowed regression from baseline before we fail the run.
DEFAULT_TOLERANCE = {
    "voice_match": 0.5,
    "ai_risk": 0.5,  # ai_risk is lower-is-better; we fail if avg goes UP by this much.
    "platform_fit": 0.5,
    "specificity": 0.5,
    "regional_english_fit": 0.5,
    "pass_rate": 0.10,  # Allow pass-rate to drop by at most 10 percentage points.
}


@dataclass
class SeedResult:
    seed_id: str
    persona_id: str
    topic: str
    draft: str
    score: dict[str, Any]
    writer_elapsed_s: float
    judge_elapsed_s: float
    error: str | None = None


def _require_anthropic_key() -> None:
    if not anthropic_available():
        raise RuntimeError(
            "ANTHROPIC_API_KEY not set or is a placeholder. Evals require a real "
            "Anthropic key — silent mock content is disallowed."
        )
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not strip_valid_key(key):
        raise RuntimeError(
            "ANTHROPIC_API_KEY missing at the env level. Writer calls Anthropic "
            "directly; set a real key before running the eval."
        )


def _load_seeds() -> dict[str, Any]:
    with SEEDS_PATH.open() as f:
        return json.load(f)


def _resolve_persona(seeds_doc: dict[str, Any], persona_id: str) -> dict[str, Any]:
    personas = seeds_doc.get("personas") or {}
    if persona_id not in personas:
        raise KeyError(f"Seed references unknown persona_id: {persona_id!r}")
    return personas[persona_id]


async def _run_one_seed(seed: dict[str, Any], persona: dict[str, Any]) -> SeedResult:
    topic = seed["topic"]
    seed_id = seed["id"]
    platform = seed.get("platform", "linkedin")
    content_type = seed.get("content_type", "post")

    writer_t0 = time.perf_counter()
    draft_payload = await run_writer(
        platform=platform,
        content_type=content_type,
        commander_output=seed["commander_output"],
        scout_output=seed["scout_output"],
        thinker_output=seed["thinker_output"],
        persona_card=persona,
        user_id="",
    )
    writer_elapsed = time.perf_counter() - writer_t0

    draft = ""
    if isinstance(draft_payload, dict):
        draft = str(draft_payload.get("draft", "")).strip()
    elif isinstance(draft_payload, str):
        draft = draft_payload.strip()

    if not draft:
        return SeedResult(
            seed_id=seed_id,
            persona_id=seed["persona_id"],
            topic=topic,
            draft="",
            score={},
            writer_elapsed_s=writer_elapsed,
            judge_elapsed_s=0.0,
            error="Writer returned empty draft",
        )

    judge_t0 = time.perf_counter()
    try:
        score: JudgeScore = score_draft(
            draft=draft,
            persona_card=persona,
            topic=topic,
            platform=platform,
            content_type=content_type,
        )
        judge_elapsed = time.perf_counter() - judge_t0
    except JudgeError as exc:
        return SeedResult(
            seed_id=seed_id,
            persona_id=seed["persona_id"],
            topic=topic,
            draft=draft,
            score={},
            writer_elapsed_s=writer_elapsed,
            judge_elapsed_s=time.perf_counter() - judge_t0,
            error=f"Judge error: {exc}",
        )

    return SeedResult(
        seed_id=seed_id,
        persona_id=seed["persona_id"],
        topic=topic,
        draft=draft,
        score=score.as_dict(),
        writer_elapsed_s=writer_elapsed,
        judge_elapsed_s=judge_elapsed,
    )


def _aggregate(results: list[SeedResult]) -> dict[str, Any]:
    scored = [r for r in results if r.score and not r.error]
    n = len(scored)
    if n == 0:
        return {
            "n_scored": 0,
            "n_errors": len(results),
            "averages": {},
            "pass_rate": 0.0,
        }
    fields = ("voice_match", "ai_risk", "platform_fit", "specificity", "regional_english_fit")
    averages = {
        f: round(sum(r.score[f] for r in scored) / n, 3) for f in fields
    }
    passes = sum(1 for r in scored if r.score.get("overall_pass"))
    return {
        "n_scored": n,
        "n_errors": len(results) - n,
        "averages": averages,
        "pass_rate": round(passes / n, 3),
    }


def _compare_to_baseline(
    aggregate: dict[str, Any], baseline: dict[str, Any]
) -> tuple[bool, list[str]]:
    if not baseline:
        return True, []
    tol = {**DEFAULT_TOLERANCE, **(baseline.get("tolerance") or {})}
    base_avg = baseline.get("averages") or {}
    cur_avg = aggregate.get("averages") or {}
    failures: list[str] = []

    # Higher-is-better fields: fail if cur drops below (base - tol).
    for f in ("voice_match", "platform_fit", "specificity", "regional_english_fit"):
        base_v = base_avg.get(f)
        cur_v = cur_avg.get(f)
        if base_v is None or cur_v is None:
            continue
        if cur_v < base_v - tol[f]:
            failures.append(
                f"{f}: {cur_v:.2f} < baseline {base_v:.2f} - tol {tol[f]:.2f}"
            )

    # ai_risk is lower-is-better: fail if cur rises above (base + tol).
    base_ar = base_avg.get("ai_risk")
    cur_ar = cur_avg.get("ai_risk")
    if base_ar is not None and cur_ar is not None:
        if cur_ar > base_ar + tol["ai_risk"]:
            failures.append(
                f"ai_risk: {cur_ar:.2f} > baseline {base_ar:.2f} + tol {tol['ai_risk']:.2f}"
            )

    # Pass rate: fail if pass_rate drops more than tolerance.
    base_pr = baseline.get("pass_rate")
    cur_pr = aggregate.get("pass_rate")
    if base_pr is not None and cur_pr is not None:
        if cur_pr < base_pr - tol["pass_rate"]:
            failures.append(
                f"pass_rate: {cur_pr:.2f} < baseline {base_pr:.2f} - tol {tol['pass_rate']:.2f}"
            )

    return not failures, failures


async def run_all() -> tuple[list[SeedResult], dict[str, Any]]:
    seeds_doc = _load_seeds()
    results: list[SeedResult] = []
    for seed in seeds_doc["seeds"]:
        persona = _resolve_persona(seeds_doc, seed["persona_id"])
        logger.info("Running seed %s (persona=%s)", seed["id"], seed["persona_id"])
        res = await _run_one_seed(seed, persona)
        if res.error:
            logger.error("Seed %s failed: %s", seed["id"], res.error)
        else:
            logger.info(
                "Seed %s scored: voice=%d ai_risk=%d platform=%d spec=%d region=%d pass=%s",
                seed["id"],
                res.score.get("voice_match", -1),
                res.score.get("ai_risk", -1),
                res.score.get("platform_fit", -1),
                res.score.get("specificity", -1),
                res.score.get("regional_english_fit", -1),
                res.score.get("overall_pass"),
            )
        results.append(res)
    aggregate = _aggregate(results)
    return results, aggregate


def _write_report(
    results: list[SeedResult],
    aggregate: dict[str, Any],
    seeds_version: str,
) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = REPORTS_DIR / f"report-{ts}.json"
    doc = {
        "timestamp": ts,
        "seeds_version": seeds_version,
        "aggregate": aggregate,
        "seeds": [asdict(r) for r in results],
    }
    out_path.write_text(json.dumps(doc, indent=2) + "\n")
    return out_path


def _load_baseline() -> dict[str, Any]:
    if not BASELINE_PATH.exists():
        return {}
    return json.loads(BASELINE_PATH.read_text())


def _write_baseline(aggregate: dict[str, Any], seeds_version: str) -> None:
    doc = {
        "seeds_version": seeds_version,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "n_scored": aggregate["n_scored"],
        "averages": aggregate["averages"],
        "pass_rate": aggregate["pass_rate"],
        "tolerance": DEFAULT_TOLERANCE,
    }
    BASELINE_PATH.write_text(json.dumps(doc, indent=2) + "\n")


def main() -> int:
    logging.basicConfig(
        level=os.environ.get("EVAL_LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    parser = argparse.ArgumentParser(description="Run the wedge content eval harness.")
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="Write the aggregate of this run to baseline.json.",
    )
    parser.add_argument(
        "--no-baseline-check",
        action="store_true",
        help="Skip baseline comparison (still writes report).",
    )
    args = parser.parse_args()

    try:
        _require_anthropic_key()
    except RuntimeError as exc:
        logger.error("%s", exc)
        return 2

    seeds_doc = _load_seeds()
    seeds_version = str(seeds_doc.get("version", "unknown"))

    results, aggregate = asyncio.run(run_all())
    report_path = _write_report(results, aggregate, seeds_version)
    logger.info("Report written: %s", report_path)

    if aggregate["n_errors"] > 0:
        logger.error("Eval had %d errored seeds — failing.", aggregate["n_errors"])
        return 3

    if args.update_baseline:
        _write_baseline(aggregate, seeds_version)
        logger.info("Baseline updated: %s", BASELINE_PATH)
        return 0

    if args.no_baseline_check:
        logger.info("Skipping baseline check (--no-baseline-check).")
        return 0

    baseline = _load_baseline()
    if not baseline:
        logger.warning(
            "No baseline.json present. Run with --update-baseline once to establish one. "
            "Not treating this as a failure."
        )
        return 0

    ok, failures = _compare_to_baseline(aggregate, baseline)
    if ok:
        logger.info("Eval passes baseline. Averages: %s", aggregate["averages"])
        return 0
    logger.error("Eval regression vs baseline:")
    for f in failures:
        logger.error("  - %s", f)
    return 4


if __name__ == "__main__":
    sys.exit(main())
