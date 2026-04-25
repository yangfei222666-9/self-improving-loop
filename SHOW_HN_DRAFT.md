# Show HN post draft — next-week submission

## Timing

**Post on Tuesday or Wednesday, around 07:00-09:00 Pacific Time** (HN front-page window with most developer traffic + lowest spam density).

Avoid: Monday (flood of weekend submissions), Friday afternoon, weekends.

Check: https://news.ycombinator.com/show — make sure no near-identical "self-improving agent" post within the last 48h.

---

## Title (max 80 chars)

Candidates, ranked:

1. **`Show HN: self-improving-loop – auto-rollback when your AI agent regresses`**  *(76 chars, outcome-focused)*
2. `Show HN: Hexagram-guided rollback guard for AI agents`  *(58 chars, differentiator)*
3. `Show HN: A pure-stdlib rollback guard for AI agents`  *(54 chars, shortest)*

Pick #1 if posting to general HN. Pick #2 if the README top section clearly
shows the six-line state machine; it is more unique but invites skepticism.

---

## Body (keep tight — HN prefers ~150-300 words for Show HN)

```
I wrote this because most "self-improving AI agent" projects I tried were
actually methodology docs — they tell you to log learnings into markdown
files and hope the next agent session reads them. That's not a loop.

self-improving-loop is the runtime loop as a Python package:

  from self_improving_loop import SelfImprovingLoop
  loop = SelfImprovingLoop()
  result = loop.execute_with_improvement(
      agent_id="my-agent",
      task="handle query",
      execute_fn=my_agent_call,
  )

It wraps any callable, tracks success rate + latency in a rolling window,
triggers a config analysis when failures pile up, and — most importantly —
auto-rolls-back if the new config regresses (>10% success drop, >20%
latency increase, or 5 consecutive failures).

The more experimental/differentiated part: it includes an optional
hexagram-guided strategy. Runtime signals map into six engineering lines
(stability, efficiency, learning, routing, collaboration, governance), then
into a bounded policy patch. The patch still goes through the same canary /
rollback guard; it is a state router, not fortune telling.

Things I wanted it to be:

  - pure stdlib — you can drop it into any project without pulling in a
    framework. Zero runtime dependencies. It's about 2k lines.
  - opinion-free on where events go — the built-in TelegramNotifier is a
    stub that logs to stdout; subclass _send_message for Slack, Discord,
    email, etc.
  - safe by default — rollback is the star of the show, not an afterthought
  - adaptive per agent — a critical alerting agent shouldn't have the same
    failure tolerance as a batch classifier

Extracted from a larger project (TaijiOS, started on Chinese New Year
2026-02-17 and built with heavy AI collaboration). This piece felt general
enough to spin out.

Honest caveats:
  - 0.1.1. Smoke-tested (40 tests), but real-world battle testing is
    ongoing. Bug reports very welcome.
  - The analysis_failure() step is statistical, not LLM-based. If you want
    LLM-authored config tweaks, subclass it.

PyPI: pip install self-improving-loop
Repo: https://github.com/yangfei222666-9/self-improving-loop
MIT licensed.

Would genuinely love feedback — especially "I tried to use it for X and hit Y".
```

*(~280 words. Within HN's sweet spot.)*

---

## First comment (post it 2 minutes after submission yourself — convention)

Pre-empt the likely top skeptical question:

```
Author here. Two questions I expect and want to answer upfront:

**"Why not LiteLLM / LangChain's existing retry mechanisms?"**

Those retry on transient failures (HTTP 5xx, timeouts). This library
does something different: it watches for *semantic regression* — the
agent is technically executing, but its success rate is dropping
because an upstream behavior changed. The rollback trigger uses
rolling success-rate delta, not HTTP status. These are complementary,
not overlapping.

**"Does it need an LLM to analyze failures?"**

No. 0.1.1 uses statistical analysis (failure clustering by error
string, frequency buckets). If you want LLM-authored config tweaks,
pass an `improvement_strategy` object and call your model inside its
`analyze()` method. The base stays LLM-free.

Happy to answer anything.

MIT licensed: copy pieces into your own loop if useful; just keep the license
notice with redistributed code.
```

---

## Pre-submission checklist

- [x] README has at least one screenshot/asciinema-style recording (`assets/demo/self_improving_loop_demo.svg` + `.cast` + `.txt`)
- [ ] `pip install self-improving-loop` actually works from PyPI (upload wheel + sdist first)
- [ ] TestPyPI dry-run works before production PyPI release
- [ ] GitHub repo description is set (use the PyPI one-liner)
- [ ] Topics set: `ai-agents`, `self-improving`, `feedback-loop`, `python`, `llm`, `autonomous-agents`
- [x] CHANGELOG.md with 0.1.1 entry
- [ ] `tests/` passes (currently 40/40)
- [ ] LICENSE file in repo root (MIT, already there)
- [ ] Sanity-run: `python -c "from self_improving_loop import SelfImprovingLoop; SelfImprovingLoop()"`

---

## If it hits front page

Replies to prepare:

- "How does this compare to CrewAI's feedback?" → CrewAI bundles this into agent orchestration. self-improving-loop is orthogonal — wrap any `execute_fn`, orchestration is your problem.
- "Is this just a retry wrapper?" → Retry is one failure; this is behavior-drift detection across a window.
- "What's the 346-heartbeat claim from the parent project?" → That's TaijiOS's Ising Heartbeat experiment, not this library. Read about it at [TaijiOS repo].
- Anyone mentioning OpenClaw → "TaijiOS runs on OpenClaw but this package is platform-agnostic."

First 24h operating rule:

- Refresh comments every 15 minutes for the first 6 hours.
- Respond to substantive criticism within 30 minutes if awake.
- Do not get defensive; convert criticism into issues or README fixes.
- If a real bug is reported, acknowledge it, patch, release, then reply with the fix link.

---

## If nobody upvotes (likely outcome, statistical)

Don't delete. Don't resubmit immediately (HN rate-limits). Wait 1-2 weeks,
improve README based on any lurker feedback, add a demo gif, try again with
a different title angle (maybe outcome-focused: "auto-rollback when your AI
agent regresses").

Alternatively, post to:
- Reddit r/LocalLLaMA (more forgiving audience for AI tooling)
- Reddit r/Python (neutral audience)
- lobste.rs (if you have an invite)
- DEV.to (longer-form post + cross-link)
