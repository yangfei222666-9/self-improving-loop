# External Repro: Regression Guard / Rollback

This repo is currently being validated as a small reliability layer for AI agents.

The target behavior is narrow:

```text
trace failures -> detect regression -> guarded change -> rollback -> event trail
```

This is not a benchmark claim and not a full agent framework. The goal of this repro is to find install friction, unclear docs, and places where rollback evidence is missing.

## What to Run

Use a clean Python environment:

```bash
git clone https://github.com/yangfei222666-9/self-improving-loop.git
cd self-improving-loop

python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .

python examples/regression_rollback_demo.py --data-dir .repro-demo
python examples/verify_regression_rollback_event_trail.py .repro-demo/regression_rollback_event_trail.jsonl
```

Expected output shape:

```text
baseline pass
failure detected
improvement proposed
backup created
patch applied
quality worse
rollback executed
final status recovered
event trail written: /path/to/self-improving-loop/.repro-demo/regression_rollback_event_trail.jsonl
demo data dir: /path/to/self-improving-loop/.repro-demo
verdict=ok
record_count=...
has_trace=true
has_rollback=true
has_strategy_restore=true
final_recovered_ok=true
```

The important proof is not the console text. The verifier must return `verdict=ok`, `has_trace=true`, `has_rollback=true`, and `final_recovered_ok=true`.

## Minimal Test

```bash
python -m pip install pytest
python -m pytest tests/test_examples.py -q
```

Expected:

```text
9 passed
```

## What Feedback Is Useful

Please open an `External Repro Report` issue if any of these happen:

- Install fails.
- `examples/regression_rollback_demo.py` does not run.
- Demo output says rollback happened but no event trail exists.
- Event trail exists but does not contain enough evidence to audit what changed.
- You can run it, but the API is not obvious for a LangGraph / CrewAI / Hermes / custom agent node.

## Useful Report Fields

Paste these into the issue:

```text
OS:
Python version:
Install command:
Command run:
Full output:
Event trail path:
Did rollback restore the previous config? yes/no/unclear
Where would you connect this in your agent stack?
```

## Current Known Limits

- This repro validates the runnable rollback demo, not the entire project surface.
- Full repository test collection may include unrelated experimental files. For external repro, start with `tests/test_examples.py`.
- The fixed `.repro-demo` path is intentional. It makes the event trail easier to inspect and avoids relying on a temporary directory that may be cleaned by the OS.
- The project is early. The useful question is not "is this complete?" but "does the rollback evidence make agent regression easier to debug?"
