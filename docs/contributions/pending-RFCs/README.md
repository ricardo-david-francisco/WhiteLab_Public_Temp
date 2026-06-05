# Pending RFCs

This folder is the **design backlog** for WhiteLab. Each file is a
proposal that has been triaged out of an Issue (or out of the
unified critique) and not yet executed. RFCs follow a uniform
shape so they can be skimmed in any order.

## File naming

`RFC-NNNN-<short-slug>.md` — four-digit zero-padded sequence.
Allocate the next number when you create the file; do not renumber.

## RFC template (copy when starting a new one)

```markdown
# RFC-NNNN — <Title>

* **Status**       : Draft | In review | Accepted | Rejected | Superseded
* **Author**       : <handle>
* **Created**      : YYYY-MM-DD
* **Last updated** : YYYY-MM-DD
* **Tracking issue**: #NN
* **Supersedes**   : —
* **Severity**     : Critical | High | Medium | Low | n/a
* **Hardware**     : <none | UPS | NIC | …>

## 1. Problem
## 2. Background
## 3. Proposal
## 4. Alternatives considered
## 5. Risks
## 6. Acceptance criteria
## 7. Rollout plan
## 8. References
```

## Lifecycle

1. **Draft** — file lives here, linked from a tracking Issue.
2. **In review** — comments and amendments happen on the PR that
   modifies the RFC file (RFCs are not edited in place; every change
   is a PR).
3. **Accepted** — the RFC is merged into the relevant
   [`docs/architecture/`](../../architecture/) document and this
   stub is replaced with a one-line pointer.
4. **Rejected / Superseded** — moved to `pending-RFCs/_archive/`
   with a closing note.

## Currently open

| ID                                          | Title                                            | Severity | Status |
| ------------------------------------------- | ------------------------------------------------ | -------- | ------ |
| [RFC-0001](RFC-0001-mobile-capture-flow.md) | Mobile capture flow (no Google Keep)             | n/a      | Draft  |
| [RFC-0002](RFC-0002-n305-auto-power-on.md)  | N305 auto power-on after AC loss                 | High     | Draft  |
| [RFC-0003](RFC-0003-fanless-ups-nut.md)     | Fanless UPS + NUT graceful-shutdown choreography | High     | Draft  |
| [RFC-0004](RFC-0004-notebooklm-digest.md)   | NotebookLM digest pipeline                       | Medium   | Draft  |
