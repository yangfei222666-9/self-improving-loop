# Launch Observation 24H · self-improving-loop v0.1.1

Status: `active`
Release: https://github.com/yangfei222666-9/self-improving-loop/releases/tag/v0.1.1
Window: `2026-04-25T14:06:58Z` → `2026-04-26T14:06:58Z`
Local window: `2026-04-25 22:06:58 +0800` → `2026-04-26 22:06:58 +0800`

Purpose: track external signal after launch with evidence, not mood.

Do not rewrite positioning based on feelings during this window. Append evidence here.

---

## Baseline Snapshot

Recorded at: `2026-04-26T00:21:31+0800`

| Metric | Value | Evidence / Note |
|---|---:|---|
| X post URL | https://x.com/jiuxiao79/status/2048043783431021014 | Captured from the account profile page. |
| X views | `10` | Visible profile metric at `2026-04-26 00:28 +0800`. |
| X replies | `0` | Visible profile metric at `2026-04-26 00:28 +0800`. |
| X reposts | `0` | Visible profile metric at `2026-04-26 00:28 +0800`. |
| X likes | `0` | Visible profile metric at `2026-04-26 00:28 +0800`. |
| GitHub stars | `0` | `gh repo view ... --json stargazerCount` |
| GitHub forks | `0` | `gh repo view ... --json forkCount` |
| GitHub watchers | `0` | `gh repo view ... --json watchers` |
| Open issues | `8` | Existing repo issues; all visible issues were created before release day. |
| New issues since release | `0` | No issue created after `2026-04-25T14:06:58Z` in the latest issue query. |
| External comments captured | `0` | No non-owner issue comments captured in repo query. |
| Wheel downloads | `1` | `self_improving_loop-0.1.1-py3-none-any.whl` |
| Source downloads | `0` | `self_improving_loop-0.1.1.tar.gz` |

Release assets at baseline:

| Asset | Downloads |
|---|---:|
| `self_improving_loop-0.1.1-py3-none-any.whl` | `1` |
| `self_improving_loop-0.1.1.tar.gz` | `0` |

---

## Observation Log

Append one row per real external signal. Do not count internal edits as traction.

| Time (+0800) | Channel | Signal | Evidence URL / ID | Action Taken | Follow-up |
|---|---|---|---|---|---|
| 2026-04-26 00:21 | GitHub | Baseline captured: 0 stars, 0 forks, 1 wheel download, 0 new post-release issues | This file | Created observation ledger | Capture X post URL |
| 2026-04-26 00:28 | X | Canonical post captured: 10 views, 0 replies, 0 reposts, 0 likes | https://x.com/jiuxiao79/status/2048043783431021014 | Updated baseline metrics | Re-check at +6h / +24h |
| 2026-04-26 00:28 | X | Launch copy drift: post says `42 tests`; release/CI copy uses `45 tests` | https://x.com/jiuxiao79/status/2048043783431021014 | Recorded drift; do not rewrite metrics from memory | Use `45 tests` in future copy |

---

## Follow-up Tasks

| Status | Task | Owner | Evidence / Stop Condition |
|---|---|---|---|
| DONE | Capture canonical X post URL | Codex via Computer Use | https://x.com/jiuxiao79/status/2048043783431021014 |
| TODO | Re-check GitHub stars / forks / release downloads at +6h | Codex | Append snapshot row |
| TODO | Re-check GitHub stars / forks / release downloads at +24h | Codex | Append final 24h row |
| TODO | Use corrected `45 tests` count in future launch copy | Codex | No new post repeats the `42 tests` drift |
| TODO | If someone asks for integration, add one adapter example before changing positioning | Codex | New issue/comment or X reply asks for LangGraph/CrewAI/AutoGen/MCP |
| HOLD | Do not rewrite README positioning during the 24h window without external evidence | Codex | Only unlock if a real user misunderstands a specific claim |

---

## Snapshot Command Notes

Use these commands when refreshing the observation log:

```bash
gh repo view yangfei222666-9/self-improving-loop \
  --json stargazerCount,forkCount,watchers,issues,description,url

gh api repos/yangfei222666-9/self-improving-loop/releases/tags/v0.1.1 \
  --jq '{tag_name:.tag_name,html_url:.html_url,published_at:.published_at,assets:[.assets[]|{name:.name,download_count:.download_count}]}'

gh issue list --repo yangfei222666-9/self-improving-loop \
  --state all --limit 20 --json number,title,state,createdAt,comments,url
```

Interpretation rules:

- A star is a weak signal, not validation.
- A download is stronger than a star but still not usage proof.
- An issue/comment/question is stronger than both because it exposes a user path.
- Internal commits do not count as external signal.
- If no signal appears in 24h, do not rebrand immediately; add one adapter example and do one targeted outreach pass.
