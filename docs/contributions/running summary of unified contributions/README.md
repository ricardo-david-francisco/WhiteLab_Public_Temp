# Running Summary of Unified Contributions

A pair of evergreen documents that synthesise everything the project's
agentic contributors have produced so far, written in professional
technical-documentation voice.

These are **the canonical narrative views** of WhiteLab. Specifications
and policies still live in [`docs/architecture/`](../../architecture/),
[`docs/research/`](../../research/), and
[`docs/threat-model/`](../../threat-model/); the documents here exist
to answer two questions an outsider — or the operator after time
away — needs an answer to before reading anything else:

1. *What is this thing, end to end, and why does it look this way?*
   → [unified deep dive/unified-deep-dive.md](unified%20deep%20dive/unified-deep-dive.md) — start with the **Quick read** bullets at the top.
2. *Where are its weak points and what should we change?*
   → [unified critique/unified-critique.md](unified%20critique/unified-critique.md) — start with the **Quick read** bullets at the top.

Both documents now begin with a topic-level bullet index that
hyperlinks straight to the relevant section, so a returning operator
can skim the headlines in under a minute and dive only into the
sections that matter today.

> **Where the roadmap lives.** Capture, prioritisation, and CI
> enforcement of these critiques are described in
> [`docs/roadmap/README.md`](../../roadmap/README.md). Pending design
> proposals derived from the critique are in
> [`../pending-RFCs/`](../pending-RFCs/).

## Editorial rules

* **Single living file per kind.** New transcripts are merged into
  the existing document by topic. We do not append per-session
  sections; we rewrite the affected sections.
* **Professional voice.** No dialogue, no "Speaker 1 / Speaker 2",
  no podcast framing. Compress the pedagogy from the transcripts
  into terse, high-information prose.
* **Cross-link the canonical sources.** Every claim should
  reference `docs/architecture/`, `docs/research/`, or
  `docs/threat-model/` where the underlying specification lives.
* **Versioned.** Each document carries a `Version` and `Date`
  header at the top. Increment on substantive merges; a typo fix
  is not a version bump.

## Refresh protocol

When a new NotebookLM transcript lands in [`../notebooklm/`](../notebooklm/):

1. Read the transcript end to end.
2. For each topic it addresses, locate the matching section in the
   relevant unified document and rewrite it to incorporate the new
   material — adding nuance, not paragraphs.
3. If a topic is genuinely new, add a section in the right place
   (deep dive: chronological / structural; critique: by severity
   bucket).
4. Update the front-matter date and bump the version.
5. Commit with a message that names the source transcript(s) merged.
