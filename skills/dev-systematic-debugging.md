# Ei Dev Skill — Systematic Debugging

- **Source:** `obra/superpowers` → `skills/systematic-debugging/SKILL.md`
- **Source URL:** https://github.com/obra/superpowers/tree/main/skills/systematic-debugging
- **License:** MIT (Copyright (c) 2025 Jesse Vincent) — adapted with attribution, no verbatim copy.
- **Trigger:** Use when encountering any bug, test failure, or unexpected behavior, BEFORE proposing fixes.

## Iron law

No fixes without root-cause investigation first. Symptom fixes are failure.
Especially under time pressure, after 2+ failed fix attempts, or when a "quick fix" looks obvious.

## Phase 1 — Root cause (must complete before any fix)

1. **Read the error fully.** Don't skip tracebacks. Note file, line, error type, message.
   - Get code output via `execute_python_code(code, timeout)`; read `stdout` + `stderr` + exit code.
2. **Reproduce with a minimal snippet.** Shrink the failing case to the smallest `execute_python_code` snippet that still fails. If not reproducible, gather more data — do not guess.
3. **Check recent changes.** Re-read the file via `read_local_document(file_path)` and compare against what the user says changed. On Windows, suspect: path separators (`\` vs `/`), encoding (use `encoding="utf-8"`), CRLF line endings, case-insensitive filenames.
4. **Trace data flow backward.** Starting from the bad value in the traceback: what called this, with what argument? Keep walking up until the origin. Fix at the source, not at the symptom.

## Phase 2 — Pattern

1. Find similar working code in the same file/project (`read_local_document`).
2. Identify the exact difference between working and broken usage.
3. If implementing a known pattern, re-read the reference completely before applying.

## Phase 3 — Hypothesis (single, testable)

1. State ONE theory: "I believe X causes Y because …".
2. Design the smallest `execute_python_code` snippet that confirms or refutes it (e.g. print the suspect value / type).
3. If refuted, form a new hypothesis — do not stack fixes.

## Phase 4 — Implement

1. Write the fix with `write_local_file` (requires user confirmation; announce it).
2. Re-run the Phase-1 reproduction snippet via `execute_python_code` to verify.
3. Re-run any related checks; report what passed.

## Ei sandbox constraints (code_runner.py)

- `execute_python_code` runs `python -I -c <code>`, timeout 2–30 s, secrets stripped from env.
- Blocked: `subprocess, ctypes, socket, threading, multiprocessing, winreg, pty`, plus `eval/exec/__import__/os.system` and dunder-reflection attributes. Never propose these in fixes.
- No `pip install`, no network-dependent fixes. Prefer stdlib-only solutions.

## Stop rules

- 3+ failed fix attempts → stop fixing; question the approach/architecture, re-do Phase 1.
- Truly environmental issue (missing file, wrong interpreter) → document what was checked, add a clear error message / guard, do not fake a fix.
