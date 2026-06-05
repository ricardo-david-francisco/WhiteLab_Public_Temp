# Contributions

Curated, agent-assisted summaries and critiques of the WhiteLab project.
The goal of this folder is to keep an evergreen, narrative-style
synthesis of the architecture alongside the canonical specs in
[`docs/architecture/`](../architecture/), [`docs/research/`](../research/),
and [`docs/threat-model/`](../threat-model/).

This material is **explanatory**, not normative. The IaC parser and the
fortress agent must never read from this directory — see the unified
critique §6 for the split-brain rule.

## Layout

```text
docs/contributions/
├── notebooklm/                                # Raw, per-session AI outputs (transcripts)
│   ├── Deep_Dive/                             #   Long-form narrated walkthroughs
│   ├── Critique/                              #   Targeted findings + remediations
│   └── Debate/                                #   Multi-position discussions (when produced)
└── running summary of unified contributions/  # Consolidated, human-edited synthesis
    ├── unified deep dive/                     #   One end-to-end document for the whole project
    │   └── unified-deep-dive.md
    └── unified critique/                      #   One consolidated critique document
        └── unified-critique.md
```

## Conventions

| Folder                                 | Voice                                               | Cadence |
| -------------------------------------- | --------------------------------------------------- | ------- |
| `notebooklm/Deep_Dive/`                | Conversational transcript (raw AI output)           | One file per session |
| `notebooklm/Critique/`                 | Conversational transcript (raw AI output)           | One file per session |
| `notebooklm/Debate/`                   | Conversational transcript (raw AI output)           | As produced |
| `running summary of unified .../`      | Professional technical documentation, no dialogue   | Single living document per kind |

The `running summary of unified contributions/` documents are the
**source of truth for narrative context** about the project. They
are merged from the raw transcripts on each refresh — topics are
unified, not appended. When a new transcript adds a new theme, the
unified document gains a section; when it adds a new angle on an
existing theme, that section is rewritten.

## How to refresh

1. Drop new NotebookLM outputs into the appropriate `notebooklm/`
   subfolder. Filenames follow `NN_Type_YYYYMMDD_short-title.txt`.
2. Re-merge the relevant unified document (`unified deep dive/` or
   `unified critique/`). Keep professional tone; remove podcast
   framing; merge by topic, not by source.
3. Open a PR; do not bypass the apply pipeline — these files do not
   touch the running infrastructure but they do change the
   project's narrative source of truth.

## Index

* [Unified deep dive](running%20summary%20of%20unified%20contributions/unified%20deep%20dive/unified-deep-dive.md) —
  end-to-end synthesis of the lab and the centralized brain.
* [Unified critique](running%20summary%20of%20unified%20contributions/unified%20critique/unified-critique.md) —
  consolidated findings and remediations.
