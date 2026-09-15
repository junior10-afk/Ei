# Ei Dev Skill — Code Review

- **Source:** `mattpocock/skills` → `skills/engineering/code-review/SKILL.md`
- **Source URL:** https://github.com/mattpocock/skills (skill: code-review)
- **License:** MIT (Copyright (c) 2026 Matt Pocock) — adapted with attribution, no verbatim copy.
- **Trigger:** Use when the user asks to review Python code, a file, or recent changes ("relis ce code", "review this", "vérifie mon script").

## Adapted process (Ei has no git/diff tool — single-pass review)

1. **Load the code.** Read the target via `read_local_document(file_path, max_chars)` (cap 20000). If content is truncated, read the remainder before judging.
2. **Identify the spec.** Ask or infer: what is this code supposed to do? One sentence. Judge "Spec" axis against that sentence only.
3. **Review along two axes, report separately** under `## Standards` and `## Spec` headings. Do not let one mask the other.

## Axis 1 — Standards checklist

- [ ] **Correctness:** off-by-one, wrong operator, mutable default args, unhandled `None`/empty input, infinite loops.
- [ ] **Errors:** specific `except` clauses (never bare `except:`), no silent `return None` on failure, exceptions chained with `from e`.
- [ ] **Ei sandbox fit:** code must run under `execute_python_code` — no `subprocess/socket/threading/multiprocessing/ctypes/winreg`, no `eval/exec/__import__`, no `os.system`. Flag any violation as blocking.
- [ ] **Windows fit:** paths via `pathlib` or `os.path` (never hardcoded `\` escapes), `encoding="utf-8"` on file I/O, no POSIX-only assumptions.
- [ ] **Readability (PEP 8):** descriptive names, type hints on public functions, docstrings on non-trivial functions, no clever one-liners that need explaining.
- [ ] **Resources:** files/sessions closed properly (`with` blocks), no unbounded memory growth.

## Axis 2 — Spec checklist

- [ ] Does each spec requirement have corresponding code? List requirement → lines.
- [ ] Any behavior beyond the spec (scope creep)? Flag it, don't praise it.
- [ ] Edge cases from the spec (empty input, errors) — covered or missing?
- [ ] If no spec was provided, say so and skip this axis (note it in the report).

## Report format

1. `## Standards` — findings, each with severity (blocking / suggestion) + line reference.
2. `## Spec` — requirement-by-requirement verdict, or "spec missing" note.
3. One-line summary per axis: count + worst issue. Never merge axes into a single ranking.
4. Offer the fix as a next step; do not rewrite the file unasked (`write_local_file` needs user confirmation — propose, then wait).
