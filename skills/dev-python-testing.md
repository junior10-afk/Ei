# Ei Dev Skill — Python Testing Conventions

- **Source:** `affaan-m/ECC` → `skills/python-testing/SKILL.md` (English version)
- **Source URL:** https://github.com/affaan-m/ECC (`npx skills add https://github.com/affaan-m/ECC --skill python-testing`)
- **License:** MIT (Copyright (c) 2026 Affaan Mustafa) — adapted with attribution, no verbatim copy.
- **Trigger:** Use when writing or improving Python tests — new function needs verification, bug fix needs a regression check, user asks for tests.

## Ei testing reality (no pytest assumed)

- Ei executes via `execute_python_code(code, timeout)` = `python -I -c <code>`, 2–30 s, no `pip install`, sandbox blocks `subprocess/threading/multiprocessing/socket`.
- Therefore: **verify with plain-`assert` scripts**, not pytest. Do not `import pytest` unless the user's project already has it (check by reading the project, never install it).
- If the project does use pytest, write test files with `write_local_file` (confirmation required) following the pytest conventions below, but run verification through `execute_python_code` snippets.

## Verification-script pattern (default)

```python
from target_module import add  # or paste the function under test

# Happy path
assert add(2, 3) == 5
# Edge cases: always include empty / zero / None / boundary
assert add(0, 0) == 0
assert add(-1, 1) == 0
# Error case
try:
    add("a", 1)
except TypeError:
    pass
else:
    raise AssertionError("add('a', 1) should raise TypeError")
print("ALL CHECKS PASSED")
```

Rules: one `assert` per behavior; end with a printed `ALL CHECKS PASSED` so voice summary can confirm; keep runtime < 15 s.

## TDD cycle (RED → GREEN → REFACTOR)

1. **RED:** run the check script first, watch it fail for the expected reason.
2. **GREEN:** minimal implementation via `write_local_file`; re-run, watch it pass.
3. **REFACTOR:** clean up only while checks stay green; re-run after each change.

## pytest conventions (only for pytest projects)

- Layout: `tests/test_<module>.py`, shared fixtures in `tests/conftest.py`.
- Prefer fixtures over setup/teardown duplication; use `scope="module"` for expensive setup.
- Use `@pytest.mark.parametrize` for input tables instead of copy-pasted tests.
- Mock boundaries with `unittest.mock.patch` (`return_value`, `side_effect`); use `autospec=True` to catch API misuse.
- Assert exceptions with `with pytest.raises(ValueError, match="..."):`, never bare try/except in tests.
- Coverage is informational (`pytest --cov`) — never gate Ei's answer on a coverage number.

## What to test (priority order)

1. The reported bug (regression check first).
2. Happy path + return type.
3. Boundaries: empty string/list, 0, negative, `None`, very long input.
4. Error paths: wrong type, missing file, invalid value → correct exception type.
