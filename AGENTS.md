## Agent skills

### Issue tracker

Issues are tracked on GitHub. See `docs/agents/issue-tracker.md`.

### Triage labels

Only `ready-for-agent` and `wontfix` are used. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context. See `docs/agents/domain.md`.

### Boot protocol

1. Read `docs/INDEX.md` first, then load only task-relevant memory.
2. Read `CONTEXT.md` for domain language, business concepts, and naming ambiguity.
3. Read `docs/adr/` for architectural tradeoffs and rejected approaches.
4. Read `docs/flows/` for end-to-end business processes.
5. Keep Markdown in the repo as the memory source of truth.

### Memory ownership

- Stable domain terms: `CONTEXT.md`
- Architecture decisions: `docs/adr/NNNN-short-title.md`
- Product requirements: `docs/prd/`
- System/module navigation: `docs/architecture/`
- Coding and collaboration conventions: `docs/conventions/`
- Business flow knowledge: `docs/flows/`
- Gotchas and platform constraints: `docs/gotchas/`
- Temporary branch/session state: `docs/handoff/current.md`
- Uncertain memory proposals: `docs/agents/memory-patch.md`

### Privacy boundary

Never write real private data to project memory: phone numbers, user IDs, raw user content, payment-sensitive data, production secrets, or unsanitized logs.

### Rules
- if you need to make changes of the code has been manually modified, confirm with the user first.
