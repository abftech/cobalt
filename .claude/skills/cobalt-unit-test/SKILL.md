---
name: cobalt-unit-test
description: Write unit tests for a Cobalt app feature following the project's custom test framework. Use when asked to write, add, or scaffold unit tests for any app in this project.
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
Patch at the **method level** using `patch.object`, not at the `requests` level:

```python
from unittest.mock import patch

def test_something(self):
    xero = XeroApi()
    mock_response = {"Contacts": [{"ContactID": "abc"}]}
    with patch.object(xero, "xero_api_post", return_value=mock_response) as mock_post:
        result = xero.some_method(...)

    payload = mock_post.call_args[0][1]
    self.manager.save_results(status=..., ...)
```

For mock/live toggle pattern, use `contextlib.nullcontext` as the no-op:

```python
from contextlib import nullcontext

MOCK_API = True  # set at top of file

def _patch_post(instance, response):
    if MOCK_API:
        return patch.object(instance, "method_name", return_value=response)
    return nullcontext(None)
```

Tests that inspect `mock.call_args` must guard with an early return when not mocked:

```python
def test_payload_structure(self):
    if not MOCK_API:
        self.manager.save_results(status=True, test_name="... [SKIPPED]", test_description="Skipped in live mode", output="")
        return
```

## Running tests
```bash
python manage.py run_tests_unit --app <appname>
```

Now write the tests for: $ARGUMENTS
