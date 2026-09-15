# Ei Dev Skill — Python Writing Patterns

- **Source:** `affaan-m/ECC` → `skills/python-patterns/SKILL.md` (English version)
- **Source URL:** https://github.com/affaan-m/ECC (`npx skills add https://github.com/affaan-m/ECC --skill python-patterns`)
- **License:** MIT (Copyright (c) 2026 Affaan Mustafa) — adapted with attribution, no verbatim copy.
- **Trigger:** Use when writing or reviewing Python code and idiomatic structure, typing, or PEP 8 is in question.

## Core principles

1. **Readability over cleverness.** Clear names, small functions, explicit config. If a line needs explaining, rewrite it.
2. **Explicit over implicit.** No hidden side effects on import; no magic defaults.
3. **EAFP** (Easier to Ask Forgiveness): try/except around the operation, not `if key in dict` guards — except never bare.

## Mandatory checklist for generated code

- [ ] **Type hints** on all function signatures (`def f(users: list[User]) -> list[User]:`); modern builtins (`list[str]`, `dict[str, Any]`, `str | None`) for Python 3.9+.
- [ ] **Docstring** on every non-trivial function (one line: what it returns).
- [ ] **Specific exceptions only:** `except FileNotFoundError`, `except json.JSONDecodeError`; chain with `raise X(...) from e`. Never bare `except:`.
- [ ] **Custom errors** derive from one project base (`class AppError(Exception)`) when the file defines more than one error.
- [ ] **Resources** via context managers (`with open(...)`, dataclasses for data holders, context managers for setup/teardown).
- [ ] **No mutable default args** (`def f(items=None)` + `items = items or []`).
- [ ] **Comprehensions** for simple transforms; named loops when logic branches.

## Ei / Windows constraints (non-negotiable)

- Code must pass the `code_runner.py` AST sandbox: **forbidden** — `subprocess, ctypes, socket, threading, multiprocessing, winreg, pty`, `eval/exec/__import__/os.system`, dunder-reflection attrs. Use `concurrent`-free, single-threaded stdlib code.
- **Files:** `pathlib.Path` / `os.path`, always `encoding="utf-8"`, never hardcode backslash escapes or POSIX-only paths.
- **Env:** `execute_python_code` strips `*API_KEY*/*SECRET*/*TOKEN*/*PASSWORD*/*AUTH*` — never read secrets from env in generated code; take them as explicit arguments.
- **Deps:** stdlib only. Never `pip install`, never assume `aiohttp/requests/pytest` exist.
- Decorators must use `functools.wraps`; class-based decorators must call `functools.update_wrapper`.
- Async (`asyncio`) only if the caller explicitly needs it — default to synchronous code.

## No new Ei tools needed

All four dev skills run on existing tools: `read_local_document` (inspect), `write_local_file` (persist, confirmation-gated), `execute_python_code` (verify). No `Tool()` additions proposed.
