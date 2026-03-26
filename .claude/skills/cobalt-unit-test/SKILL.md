---
name: cobalt-unit-test
description: >-
  Write unit tests for a Cobalt app feature following the project's custom test framework.
  Use this whenever the user wants to test, verify, or add coverage to any feature in this
  project — even if they don't say "unit test" explicitly. Triggers include "test this",
  "I need tests for X", "can you test this function", "add test coverage", "write tests for
  the payments app", or any time new code is written and tests would be appropriate.
argument-hint: [app-name] [feature description]
---

Write unit tests for the Cobalt project following these rules exactly.

## File location
`<app>/tests/unit/unit_test_<feature>.py`

## Structure

```python
from tests.test_manager import CobaltTestManagerUnit


class <FeatureName>Tests:
    def __init__(self, manager: CobaltTestManagerUnit):
        self.manager = manager
        # Set up any fixtures needed across all tests in this class

    def test_01_<description>(self):
        result = ...
        self.manager.save_results(
            status=result == expected,  # bool
            test_name="Human-readable name",
            test_description="What this test checks",
            output=f"Got {result!r}, expected {expected!r}",
        )
```

## Rules
- **Do NOT inherit from `django.test.TestCase`** — plain class only.
- `__init__` receives `manager: CobaltTestManagerUnit`; store as `self.manager`.
- Every test method name starts with `test_` and is auto-discovered.
- Use `self.manager.save_results(status=<bool>, ...)` — **no `assert` statements**.
- Pre-built users: `self.manager.alan`, `.betty`, `.colin`, `.debbie`, `.eric`, `.fiona`, etc.
- All DB writes are wrapped in a rolled-back transaction — tests are isolated.
- Shared helpers go in `tests/unit/general_test_functions.py`.

## Mocking external APIs
Patch at the **method level** using `patch.object`, not at the `requests` level — this avoids token-refresh side effects and keeps tests clean:

```python
from unittest.mock import patch

def test_something(self):
    api = SomeExternalApi()
    mock_response = {"key": "value"}
    with patch.object(api, "method_name", return_value=mock_response) as mock_call:
        result = api.some_method(...)

    payload = mock_call.call_args[0][1]  # inspect what was sent
    self.manager.save_results(status=..., ...)
```

For services that may sometimes be tested live, use a `MOCK_API = True` flag at the top of the file and `contextlib.nullcontext` as the no-op alternative. Tests that inspect `mock.call_args` must guard with an early return when `MOCK_API` is false. See `xero/tests/unit/unit_test_xero_api.py` for the full reference pattern.

## Running tests
```bash
python manage.py run_tests_unit --app <appname>
```

Now write the tests for: $ARGUMENTS
