# NotebookLM Outputs

Raw, per-session outputs produced by NotebookLM (and equivalent
agentic tooling) about the WhiteLab project. These files are the
**input** to the consolidated documents in
[`../running summary of unified contributions/`](../running%20summary%20of%20unified%20contributions/);
they are not themselves the source of truth for anything operational.

## Layout

```text
notebooklm/
├── Deep_Dive/   # End-to-end narrated walkthroughs of the project
├── Critique/    # Targeted findings + suggested remediations
└── Debate/      # Multi-position discussions (when produced)
```

## File naming

`NN_Type_YYYYMMDD_short-title.ext`

* `NN` — two-digit sequence within the folder.
* `Type` — `Deep-dive`, `Critique`, or `Debate`.
* `YYYYMMDD` — date the source session was generated.
* `short-title` — kebab-or-space title; keep it under ~60 chars.
* `ext` — usually `.txt` for transcripts.

## Status

The transcript bodies are **append-only**. Once a transcript is
committed the spoken text is not edited; corrections live in the
unified summaries. This preserves a faithful record of what each
generation pass produced and lets us diff how the project's story
evolves over time.

### Editorial header block (allowed exception)

Each `.txt` may carry one editorial header block at the top of the
file, clearly delimited by `===` rules and ending with a
`CONVENTION` paragraph that names itself as editorial. The header
contains:

* file metadata (name, type, date, duration);
* an INDEX of chapters mapped to approximate transcript timestamps;
* a KEY TOPICS bullet list summarising the discussion.

Headers may be regenerated whenever the unified summaries are
refreshed. They are the only mutable surface in this directory; the
transcript bytes below the divider remain frozen.

## Cross-references

* Unified, prose-form synthesis of every deep-dive transcript:
  [`../running summary of unified contributions/unified deep dive/unified-deep-dive.md`](../running%20summary%20of%20unified%20contributions/unified%20deep%20dive/unified-deep-dive.md).
* Unified critique with severity, mechanism, fix, and acceptance
  criteria per finding:
  [`../running summary of unified contributions/unified critique/unified-critique.md`](../running%20summary%20of%20unified%20contributions/unified%20critique/unified-critique.md).
* Pending RFCs spawned by these critiques:
  [`../pending-RFCs/`](../pending-RFCs/).
