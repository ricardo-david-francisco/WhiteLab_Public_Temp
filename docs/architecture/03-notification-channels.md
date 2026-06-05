# Notification channels — pluggable adapter abstraction

> **Reference architecture for `tools/notify/`.** Companion to
> [ADR-0001](../decisions/ADR-0001-approval-channel.md).

## One-paragraph summary

The fortress agent and several GitHub Actions workflows need to
deliver short, time-sensitive messages to the operator: a TOTP
prompt, a critique-imported issue summary, a CI failure badge. The
channel through which those messages travel is a configuration
detail — not an architectural one. We wrap it behind a single Python
entry point (`notify.py`) that fans out to one or more adapters
declared in `channels.yaml`. The default channel is **email over
STARTTLS**; ntfy, Signal and a no-op GitHub-mobile adapter ship as
stubs.

## Why this is a pillar, not a detail

Three distinct forces converged on the same answer:

1. **Operator preference.** This operator does not use Telegram,
   refuses Discord for ops, and treats email as the lowest-friction
   universal inbox. Hard-coding any single channel would either
   fight that preference or force a code change every time it
   shifts.
2. **Free-tier discipline.** The whole automation surface must run
   on free-tier GitHub plus self-hosted LXCs. Every adapter we ship
   is either universal infrastructure (SMTP) or self-hostable
   open-source (ntfy, signal-cli) — never a SaaS account that can
   be suspended.
3. **Zero-trust composability.** Notifications cross the trust
   boundary into the operator's personal devices. A single channel
   is a single attack surface; supporting parallel channels means
   one outage or compromise does not silence the whole apply path.

## The contract

Every adapter implements:

```python
def send(title: str, body: str, severity: str, config: dict) -> None:
    ...
```

* `severity` ∈ `{info, warning, critical}` — adapters may map this
  to per-platform priority (ntfy `Priority` header, mail subject
  prefix, Signal message tag).
* The function raises on failure; `notify.py` catches per-adapter
  and continues.
* No top-level imports beyond the standard library and `yaml`. Each
  adapter lazy-imports its own dependencies (e.g. `signal-cli`
  subprocess) at call time, so a disabled adapter has zero cost.

## File layout

```text
tools/notify/
├── README.md               # operator-facing usage + adapter index
├── channels.yaml           # the only knob
├── notify.py               # entry point (fan-out, dry-run, lazy import)
└── adapters/
    ├── __init__.py
    ├── email.py            # default — SMTP/STARTTLS, password from env
    ├── ntfy.py             # stub — self-hosted ntfy
    ├── signal.py           # stub — signal-cli wrapper
    └── github.py           # stub — no-op (mobile notifications only)
```

## Failure modes & their responses

| Mode | Adapter behaviour | Caller behaviour |
| --- | --- | --- |
| Misconfiguration | `RuntimeError` with explicit message | `notify.py` logs to stderr, continues with next adapter |
| Network outage | `OSError`/`socket.timeout` | same |
| Credential rotation in flight | `smtplib.SMTPAuthenticationError` | same |
| Adapter module missing entirely | `ImportError` | logged, skipped |
| All adapters fail | exit code 1 | the calling workflow / agent decides whether to retry, fall back to GitHub-only, or escalate to a documented break-glass procedure |

## What lives here vs in the fortress agent

* **Here:** the abstraction (entry point, adapter contract, default
  email adapter, stubs).
* **In the fortress agent (separate RFC):** the runtime wiring —
  which severity triggers which fan-out shape, retry budgets,
  rate-limiting, audit logging.

This split keeps the abstraction itself testable in CI without
needing the agent stack, and it lets the agent move forward on
notification UX without re-touching the channel layer.
