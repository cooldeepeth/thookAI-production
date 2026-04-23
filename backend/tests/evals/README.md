# Wedge content eval harness

LLM-as-judge eval for the Writer agent. Guards the core wedge promise:
"doesn't sound like ChatGPT, sounds like the creator".

## What it does

1. Loads `seeds.json` — 6 representative topic × persona combos for the
   LinkedIn wedge ICP (non-native-English solo founders building in public).
2. Calls `agents.writer.run_writer` directly with each seed's pre-built
   commander/scout/thinker outputs, so only the Writer varies between runs.
3. Sends each draft to `judge.score_draft` which scores on five dimensions:
   - `voice_match` (0-10, higher better)
   - `ai_risk` (0-10, lower better)
   - `platform_fit` (0-10, higher better)
   - `specificity` (0-10, higher better)
   - `regional_english_fit` (0-10, higher better)
4. Aggregates, writes a timestamped report to `reports/`, and compares to
   `baseline.json`. Regression beyond the per-field tolerance fails the run.

## Run it

Requires `ANTHROPIC_API_KEY` — not a placeholder. The harness refuses to
fall back to mock content; a missing key is a loud failure.

```bash
cd backend
export ANTHROPIC_API_KEY=sk-ant-...
python -m tests.evals.runner                       # run + compare to baseline
python -m tests.evals.runner --update-baseline     # snapshot current run AS baseline
python -m tests.evals.runner --no-baseline-check   # run + write report only
```

Exit codes:

- `0` — eval passes baseline (or no baseline, or `--update-baseline`, or `--no-baseline-check`)
- `2` — missing / invalid `ANTHROPIC_API_KEY`
- `3` — one or more seeds errored (writer or judge failure)
- `4` — regression vs baseline beyond tolerance

## Files

| File            | Purpose                                                                             |
| --------------- | ----------------------------------------------------------------------------------- |
| `seeds.json`    | Fixed seed set + persona definitions. Versioned — bump `version` when seeds change. |
| `judge.py`      | Judge prompt, response validator, `score_draft()`. Uses Claude Sonnet 4.            |
| `runner.py`     | Orchestration, aggregation, baseline comparison.                                    |
| `baseline.json` | Committed baseline averages + tolerance. Regenerate with `--update-baseline`.       |
| `reports/`      | Timestamped per-run reports. Gitignored.                                            |

## CI

See `.github/workflows/evals.yml`. The workflow runs on PRs against the
`wedge/linkedin-only` branch and fails if `runner` exits non-zero.
Requires the `ANTHROPIC_API_KEY` repository secret.

## Cost per run

6 seeds × (writer Sonnet call + judge Sonnet call) ≈ 12 Sonnet calls per
run. Rough order: $0.10–$0.30 depending on draft length. Budget the CI
workflow to run on PR open and the `wedge/linkedin-only` branch only.

## When to update the baseline

- After a deliberate improvement to any of: writer prompt, persona card
  schema, thinker output shape, model version.
- Never to hide a regression. If a run fails, diagnose first. Only update
  the baseline once the regression is either intentional or fixed.
