---
name: External Repro Report
about: Report whether the regression rollback repro works in your environment
title: "[REPRO] "
labels: external-repro
assignees: ""
---

## Repro verdict

- [ ] Works
- [ ] Fails
- [ ] Works but unclear

## Environment

- OS:
- Python version:
- Install command:
- Commit / release / branch tested:

## Commands run

```bash
python examples/regression_rollback_demo.py --data-dir .repro-demo
python examples/verify_regression_rollback_event_trail.py .repro-demo/regression_rollback_event_trail.jsonl
python -m pip install pytest
python -m pytest tests/test_examples.py -q -o addopts=''
```

## Full output

```text
Paste terminal output here.
```

## Event trail evidence

- Event trail path:
- Did the event trail include trace records? yes/no/unclear
- Did the event trail include rollback records? yes/no/unclear
- Did rollback restore the previous config? yes/no/unclear
- Verifier output:

```text
Paste verifier output here.
```

## Agent stack fit

Where would this be useful or not useful?

- [ ] LangGraph node
- [ ] CrewAI agent/task
- [ ] Hermes-style skill call
- [ ] Custom agent node
- [ ] Not useful for my stack

Why?

```text
One concrete reason is enough.
```

## What blocked adoption?

- [ ] Install friction
- [ ] API unclear
- [ ] Rollback proof unclear
- [ ] Missing integration example
- [ ] Not a real problem for my agent stack
- [ ] Other:
