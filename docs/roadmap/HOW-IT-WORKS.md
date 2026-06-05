# How the WhiteLab funnel works (noob view)

> **Read this if** you have never touched the repo before, or if you
> last touched it months ago and the moving parts blur together. Five
> minutes, no jargon, three concrete examples at the end.

## The one-sentence promise

Every thought, critique, bug, and "I should fix that someday" goes
into **GitHub Issues**, and the repo's home page is *always* an
honest mirror of what's open, what's next, and what's stuck — without
you having to remember to update anything by hand.

## The five layers of the funnel

```text
┌─────────────────────────────────────────────────────────────────┐
│ 1. CAPTURE                                                      │
│    "Shower thought" issue template on GitHub Mobile.            │
│    Two taps. status:inbox auto-applied.                         │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│ 2. AUTO-IMPORT                                                  │
│    NotebookLM critique findings -> issues, weekly + on push.    │
│    Rejection/adaptation = ADR file. No silent drops.            │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│ 3. TRIAGE                                                       │
│    You change a label: status:next, status:in-progress,         │
│    or status:blocked. That single click drives the rest.        │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│ 4. WORK                                                         │
│    status:in-progress automatically opens a draft PR.           │
│    Push commits, remove the marker, mark Ready for Review.      │
│    CI: 10 baseline checks + zero-trust SSH guard.               │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│ 5. SHIP & REFRESH                                               │
│    Squash-merge -> roadmap snapshot regenerates -> repo home    │
│    page reflects new reality within seconds. Done.              │
└─────────────────────────────────────────────────────────────────┘
```

## The daily / weekly loop

| Cadence | What runs | What you do |
| --- | --- | --- |
| **On every issue event** | `roadmap-sync.yml` regenerates `docs/roadmap/active-roadmap.md` | Nothing |
| **On every PR** | `zero-trust-guard.yml`, `docs-up-to-date.yml`, the standard 10-check suite | Push code, address CI failures |
| **On every push to master** | `roadmap-sync.yml`, `critique-sync.yml` (if the critique file changed) | Nothing |
| **Daily 06:15 + 18:15 UTC** | Roadmap snapshot safety-net | Nothing |
| **Daily 07:00 UTC** | `stale-sweeper.yml` — labels untouched issues `stale` after 14 days. Never auto-closes. | Optionally pin or revisit |
| **Mondays 06:00 UTC** | `critique-sync.yml` — re-import critique findings | Triage anything new |
| **Mondays 06:30 UTC** | `weekly-digest.yml` — opens/edits a single pinned digest issue | Read it on the bus |

## Three CI invariants you cannot accidentally break

1. **Automation.** A new feature workflow cannot disable an
   existing one. The roadmap, the critique importer and the
   weekly digest must keep running. The `stale-sweeper` must keep
   never-auto-closing.
2. **Security.** Zero-trust guard fails any PR that re-introduces
   SSH (`Port 22`, `sshd_config`, `ssh-rsa` keys, `systemctl enable
   ssh`) outside the documentation allow-list. SSH is permanently
   masked per [ADR-0002](../decisions/ADR-0002-no-ssh-ever.md).
3. **Unified.** Every PR must reference an issue (`Fixes #N`), and
   that issue must be triaged out of `status:inbox`. Override:
   the `docs-skip` label, used sparingly and visible.

## Three concrete examples

(Plus a fourth — a couch-side paste from NotebookLM — at the end.)

### Example A — "BIOS update for the N305"

You read on a forum that the N305's vendor pushed a BIOS update.
You're at the kitchen table.

1. Open GitHub Mobile → `+` → New issue → **Shower thought** template.
2. Title: "BIOS update for N305 — investigate". Body: paste the link.
3. Submit. The issue lands with `status:inbox`.
4. Next time you open the laptop, the roadmap snapshot already
   shows it under *Inbox*.
5. You change the label to `status:next` (it's small) o
   `status:in-progress` (you'll do it now). The latte
   auto-opens a draft PR — even if all that PR ever holds is a
   line in a CHANGELOG. The work is now visible.

### Example B — "Add an AdGuard LXC on the 10.20.0.0/24 DMZ"

Critique §7 already filed this finding. You read it Monday morning
in the digest.

1. The critique-importer issue is already open, labelled
   `critique`, `status:inbox`.
2. You either:
   * accept it → file an RFC, implement, merge a PR with `Closes
     #N` and the issue closes automatically, **or**
   * adapt it → open a *Decision* issue, paste the critique
     anchor (`#7-ip-plan-adguard-dmz-subnet-collision`), describe
     the alternative, write `ADR-0004-...`. The next critique-sync
     run sees the ADR's `related-critique:` block and auto-closes
     the original issue with comment `Adopts ADR-0004`.

### Example C — "OPNsense rule that needs a Telegram approval ping"

You're tempted to just hard-code Telegram into the fortress agent.
The repo says no:

1. The notify abstraction (`tools/notify/`) is already in place.
2. You add Telegram by creating `tools/notify/adapters/telegram.py`
   that satisfies the `send(title, body, severity, config)` contract.
3. You enable it in `channels.yaml` alongside email — fan-out, not
   replacement.
4. You leave [ADR-0001](../decisions/ADR-0001-approval-channel.md)
   intact: email remains the *default*; Telegram is *additional*.
   Future-you, on a Telegram outage, just sets `enabled: false` and
   carries on.

### Example D — "Paste a snippet from NotebookLM into the repo"

You're on the couch with a phone. NotebookLM (or Claude, or Gemini,
or a kind colleague) just produced a runbook that should land at
`docs/runbooks/immich.md`. You do not want to open VS Code. The repo
gives you two paths, both ending in a draft PR a human must review:

1. **Issue body channel.** Open a new issue from the *Proposal*
   template. The body already shows the shape:

   ```text
   target: docs/runbooks/immich.md

   ​```markdown
   # Immich runbook
   …
   ​```
   ```

   Submit it. The `proposal:apply` label is added automatically. The
   `proposal-apply.yml` workflow parses the body, runs the path
   allow-list and the anonymiser refusal check, and opens a draft PR
   linked to the issue with `Closes #<n>`.

2. **Inbox folder channel.** Drop the file plus a tiny manifest
   under `inbox/<slug>/`:

   ```yaml
   # inbox/add-immich-runbook/manifest.yml
   target: docs/runbooks/immich.md
   source: immich.md
   ```

   Push to `master`. Same workflow validates, copies the file into
   place, deletes `inbox/<slug>/`, and opens the draft PR.

What this funnel **cannot** do, by construction:

- It cannot write outside the allow-list (no `.github/workflows/`,
  no `tools/guards/`, no `vault/`, no `audit/`).
- It cannot land a snippet that contains a plaintext password,
  bearer token, API key, MAC, public IP, private key, or JWT — every
  proposal is run through the same regex catalog the anonymiser uses.
- It cannot auto-merge. The workflow contains zero `gh pr merge`
  calls; the PR is always opened in draft state.

Practical consequence: a hostile or careless paste at most produces
a draft PR you immediately close. There is no fast path to `master`.

## Where to look when something is weird

| Symptom | First place to look |
| --- | --- |
| Issue I just opened isn't in the roadmap | Actions tab → `Roadmap Sync` — last run status |
| PR check `zero-trust-guard` is red | `tools/guards/no-ssh.sh` output in the run log |
| PR check `docs-up-to-date` says "issue not triaged" | The linked issue still has `status:inbox`; change it or add `docs-skip` |
| Critique finding I expected isn't an issue | Run `gh workflow run critique-sync.yml --ref master` manually |
| Stale label seems wrong | `actions/stale` only labels after 14 days of *no* activity; comment to reset |

## See also

* [`docs/roadmap/README.md`](README.md) — full roadmap docs
* [`docs/decisions/README.md`](../decisions/README.md) — ADR format
* [`docs/architecture/03-notification-channels.md`](../architecture/03-notification-channels.md) — adapter abstraction
* [Top-level `README.md`](../../README.md) — repo entry point
