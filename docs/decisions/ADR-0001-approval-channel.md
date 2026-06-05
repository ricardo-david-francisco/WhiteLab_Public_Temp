---
id: ADR-0001
status: Accepted
date: 2026-05-06
supersedes: []
related-issues: []
related-critique:
  - "#2-operational-friction-at-the-totp-gate"
tags: [security, notifications, adhd]
---

# ADR-0001 — Approval-channel abstraction; default to email/SMTP

## Context

The unified critique §2 proposes Telegram as the channel through which
the operator delivers the TOTP code that unlocks the eight-gate apply
path (Gate 6). The operator does not use Telegram and refuses to take
on a chat-network dependency to operate their home network.

More generally, hard-coding *any* single channel re-introduces a
single point of failure: outage, account ban, vendor pivot, or
personal preference change all require a code change.

## Decision

We treat the approval-and-notification channel as a **pluggable
adapter** under `tools/notify/`. The default channel is **email over
SMTP** with credentials supplied by a Gmail app password (or any
other STARTTLS-capable provider) stored as the `NOTIFY_SMTP_PASS`
secret. Switching channels — to ntfy.sh on a self-hosted LXC, to
Signal via `signal-cli`, to GitHub mobile notifications only, or to
several in parallel — is a one-line edit in
`tools/notify/channels.yaml` plus the matching secret.

Concretely:

* `tools/notify/notify.py` is the single entry point; it reads
  `channels.yaml`, lazy-imports each enabled adapter, and emits the
  same payload to all of them.
* All adapters implement the same interface
  (`send(title: str, body: str, severity: str) -> None`); failure of
  one adapter does not prevent the others from delivering.
* `email` is enabled by default. `ntfy`, `signal`, `github` ship as
  no-op stubs that error loudly if enabled without configuration —
  silent failure is forbidden.

## Consequences

* The fortress-agent integration with the chosen channel is a
  follow-up RFC, not a runtime change in this PR. This ADR ships the
  *abstraction*, not the live wiring.
* The repository never references "Telegram" as the canonical
  channel. The unified critique text remains as the *finding*; this
  ADR is the *disposition*.
* We commit to keeping every adapter free-tier: email is universal,
  ntfy and Signal are OSS, the GitHub-only adapter relies on the
  existing free notifications.
* We do not store credentials in the repo. SMTP passwords live in
  GitHub Actions secrets and on the fortress agent's local secret
  store; the ADR states this contract explicitly.
* Critique §2 finding is **Adopted (adapted)**: the *gate* survives,
  the *channel* is generalised.

## Alternatives considered

* **Telegram only**, as in the original critique. Rejected: vendor
  lock-in plus operator preference.
* **GitHub mobile notifications only**, no extra adapter. Rejected:
  notifications are best-effort; the Gate-6 prompt deserves a
  delivery-confirmable channel.
* **Build a one-off Signal-only integration**. Rejected: same
  vendor-lock-in argument that ruled out Telegram.

## References

* Unified critique §2:
  [Operational Friction at the TOTP Gate](../contributions/running%20summary%20of%20unified%20contributions/unified%20critique/unified-critique.md#2-operational-friction-at-the-totp-gate).
* Adapter contract: `tools/notify/notify.py`.
* Channel configuration: `tools/notify/channels.yaml`.
