# Project Memory Index

This directory is the repo-first engineering memory layer. Its goal is to let future sessions, IDEs, and LLMs recover project context with low token cost.

## Loading Strategy

Do not read the whole repository by default. Load the smallest useful context for the task:

| Current task | Read first |
| --- | --- |
| Any new session | `CLAUDE.md` / `AGENTS.md`, this file, `README.md` |
| Domain terms / business naming | `CONTEXT.md` |
| Architecture tradeoffs / rejected approaches | `docs/adr/` |
| System structure / module navigation | `docs/architecture/` |
| Coding conventions | `docs/conventions/` |
| Business flows | `docs/flows/` |
| Platform limits / historical gotchas | `docs/gotchas/` |
| Current unfinished work | `docs/handoff/current.md` |
| Issue tracker config | `docs/agents/issue-tracker.md` |

## Memory Layers

- `CONTEXT.md`: domain language and stable concepts; keep it short.
- `docs/adr/`: architecture decisions with chosen / rejected / consequences.
- `docs/prd/`: product requirements and long-lived specs.
- `docs/architecture/`: system navigation and module relationships.
- `docs/conventions/`: shared coding and collaboration rules.
- `docs/flows/`: distilled business process knowledge.
- `docs/gotchas/`: platform limitations and risky boundaries.
- `docs/agents/`: runtime configuration (issue tracker, triage labels, domain rules) and templates.
- `docs/handoff/`: local short-term working context; usually gitignored.

## Update Discipline

After completing work with memory value, extract only stable facts:

- New domain terms: update `CONTEXT.md`.
- New architecture decisions: add `docs/adr/NNNN-short-title.md`.
- New flow knowledge: update `docs/flows/*.md`.
- New platform gotchas: update `docs/gotchas/*.md`.
- Temporary TODOs or branch state: update `docs/handoff/current.md`.
- Unsure whether something belongs in long-term memory: propose via `docs/agents/memory-patch.md`.

Do not save chat transcripts, unverified guesses, real private data, or fast-expiring command output.
