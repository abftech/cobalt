# Cobalt — Claude Code Guide

## What This Project Is

Cobalt is a Django web application for the **Australian Bridge Federation (ABF)** to administer the card game of contract bridge. It is deployed at [myabf.com.au](https://www.myabf.com.au).

It handles: club and organisational management, member payments, event entry, masterpoints, results/scoring, discussion forums, push notifications, and Xero accounting integration.

---

## Tech Stack

| Concern | Technology |
|---|---|
| Framework | Django 5.2 |
| Database | PostgreSQL via AWS RDS (psycopg2) |
| Frontend | Bootstrap 4 + **HTMX** |
| Rich text editor | Summernote |
| Payments | Stripe |
| Email delivery | AWS SES via django-ses + django-post-office (queuing) |
| Push notifications | Firebase/FCM (fcm-django) |
| File storage | AWS S3 (boto3) |
| PDF generation | ReportLab |
| Excel export | XlsxWriter |
| Monitoring | New Relic |
| WSGI server | Gunicorn (5 workers, 8 threads) |
| REST API | Django Ninja |
| 2FA | Django OTP |
| Background jobs | **Cron** (Django management commands — no Celery) |
| Deployment | AWS Elastic Beanstalk (no Docker) |

---

## Coding Conventions

### Views: function-based by default

Prefer **function-based views** (FBVs). Class-based views (CBVs) are a last resort and should only be used when Django's generic CBVs provide significant boilerplate reduction that cannot be achieved otherwise.

### HTMX is the primary interactivity mechanism

We use HTMX extensively for partial page updates instead of a full SPA framework. Most interactive UI flows use HTMX posts to views that return HTML fragments. Templates are often split into a "full page" template and an `_htmx.html` fragment variant.

#### Confirmation dialogs — use SweetAlert2, not `confirm()`

Never use the browser's native `confirm()` for destructive actions. Use SweetAlert2 instead. Load it in `{% block footer %}` and trigger HTMX programmatically via `htmx.ajax()`:

```html
{% block footer %}
    <script src="{% static "assets/js/plugins/sweetalert2.js" %}"></script>
    <script>
        function confirmDelete() {
            Swal.fire({
                title: 'Are you sure?',
                text: 'This cannot be undone.',
                icon: 'warning',
                showCancelButton: true,
                confirmButtonColor: '#d33',
                cancelButtonColor: '#3085d6',
                confirmButtonText: 'Yes, delete it'
            }).then((result) => {
                if (result.isConfirmed) {
                    htmx.ajax('POST', '{% url "app:some_view" %}', {
                        target: '#some-div',
                        values: {key: 'value'}
                    });
                }
            });
        }
    </script>
{% endblock footer %}
```

The button just calls the JS function: `<button onclick="confirmDelete()">Delete</button>` — no `hx-post` on the button itself.

#### Suppressing the "leave page?" prompt

`cobalt-core.js` registers a `beforeunload` handler that warns users about unsaved form changes. Pages that manage their own state (e.g. HTMX-driven admin tools) should suppress it by adding a hidden element anywhere in the template:

```html
<span id="ignore_cobalt_save" hidden></span>
```

### Models stay thin

Keep models as short as possible. They should define fields, `__str__`, simple properties, and `Meta`. **Business logic belongs in views** (or in `*_core.py` helper modules alongside the app's views), not in model methods.

### Register all new models in admin.py

Every new model must be added to the app's `admin.py` file so it appears in the Django admin. Add the model to the import line and call `admin.site.register(MyModel)` for it.

### No Celery — use cron + management commands

Background/scheduled work is handled by Django management commands run by cron on the EC2 instances. See examples in `notifications/management/commands/` and `organisations/management/commands/`.

### Batch job pattern

Every management command **must** follow this pattern (see `organisations/management/commands/auto_pay_batch.py` as the reference):

```python
import logging
import sys

from django.core.management.base import BaseCommand

from utils.models import BatchStatus
from utils.views.cobalt_lock import CobaltLock

logger = logging.getLogger("cobalt")


class Command(BaseCommand):
    help = "..."

    def handle(self, *args, **options):
        logger.info("<command name> starting")

        batch = BatchStatus.objects.create(command="<command_name>")
        summary_lines = []

        try:
            lock = CobaltLock("<command_name>", expiry=10)
            if not lock.get_lock():
                logger.info("<command name> already running (locked), exiting")
                sys.exit(0)

            # ... do work, appending human-readable lines to summary_lines ...

            lock.free_lock()
            lock.delete_lock()

        except Exception as e:
            logger.exception("<command name> failed with an unhandled exception")
            batch.status = BatchStatus.STATUS_FAILED
            summary_lines.append(f"\nERROR: {e}")
            batch.summary = "\n".join(summary_lines)
            batch.save()
            raise

        batch.status = BatchStatus.STATUS_SUCCESS
        batch.summary = "\n".join(summary_lines)
        batch.save()

        logger.info("<command name> finished")
```

Key rules:
- Always create a `BatchStatus` record at the start (status defaults to `STATUS_STARTED`).
- Use `CobaltLock` to prevent concurrent runs on multiple servers; call `sys.exit(0)` if lock is not acquired.
- Accumulate a human-readable `summary_lines` list throughout; join it into `batch.summary` at the end.
- The outer `try/except` catches unhandled exceptions, sets `STATUS_FAILED`, saves the summary, then **re-raises** so the error is visible in cron logs.
- On success, set `STATUS_SUCCESS` and save the batch record after releasing the lock.

### Configuration via environment variables

There is a single `cobalt/settings.py`. All environment-specific configuration is supplied via environment variables (managed by Elastic Beanstalk on AWS, and by a local `.env` or shell exports in development). Never hardcode secrets or environment-specific values.

---

## Project Structure

```
cobalt/                  # Django project root (settings, urls, wsgi)
accounts/                # Custom User model and authentication
api/                     # REST API (Django Ninja)
calendar_app/            # Calendar
club_sessions/           # Club session management
dashboard/               # User dashboard
events/                  # Event entry and management
forums/                  # Discussion forums
logs/                    # Application event logging
masterpoints/            # ABF masterpoints tracking
notifications/           # Email and push notification delivery
organisations/           # Clubs and state/national organisations
payments/                # Stripe payment processing and Bridge Credits
rbac/                    # Role-based access control
results/                 # Results and scoring
support/                 # Help desk and support tools
tests/                   # Test infrastructure (custom runner, test data)
utils/                   # Shared utilities, middleware, AWS helpers
xero/                    # Xero accounting integration
```

Each app typically has:
- `models.py` — data models (kept thin)
- `views/` — sub-module with FBVs split by feature area, plus `*_core.py` for shared business logic
- `urls.py` — URL routing
- `templates/<app>/` — HTML templates
- `management/commands/` — cron-invoked management commands
- `tests/unit/` and `tests/integration/` — test classes

---

## AWS Infrastructure

- **Elastic Beanstalk** — application hosting (no Docker; EB-native Python platform)
- **RDS (PostgreSQL)** — primary database (`RDS_*` environment variables)
- **SES** — transactional email delivery (`AWS_SES_*` settings)
- **SNS** — used for push notification infrastructure
- **S3** — media file storage

The deployment hostname is exposed as `COBALT_HOSTNAME`. Management commands that could be destructive check this value and raise `SuspiciousOperation` if accidentally run against production (`myabf.com.au` / `www.myabf.com.au`).

---

## Access Control (RBAC)

The `rbac` app provides fine-grained role-based access control. Roles follow the pattern:

```
<app>.<resource>.<object_id>.<action>
# e.g. orgs.members.42.edit
```

Views use decorator helpers like `@check_club_menu_access(check_members=True)` to gate access. Always check RBAC rather than relying on session state alone.

---

## Coding Style and Pre-commit Hooks

Code is formatted and validated automatically via **git pre-commit hooks**. Do not skip them (`--no-verify`). The hooks run:

- **black** — Python code formatting (Python 3.13)
- **flake8** — Python linting
- **djhtml** — Django template indentation
- **debug-statements** — prevents accidental committed `breakpoint()` / `pdb` calls

Run `pre-commit install` after cloning. To run hooks manually: `pre-commit run --all-files`.

### Python version

The minimum supported Python version is **3.13**. Write code that targets 3.13+ features freely — do not add compatibility shims for older versions.

### String formatting

Always use **f-strings** for string interpolation. Do not use `%` formatting or `str.format()`. Do not concatenate strings with `+` when an f-string can be used instead.

---

## Testing

Tests use a **custom framework** (no pytest) built on top of Django's test client and Selenium.

Run tests via management commands:
```bash
# Unit tests
python manage.py run_tests_unit --app <appname>

# Integration / Selenium tests
python manage.py run_tests_integration --app <appname> --browser chrome --headless

# Smoke tests
python manage.py run_tests_smoke --script <script_name>
```

Test data is seeded with `python manage.py add_test_data`. Pre-populated test users have numeric system numbers (100–115) and password `F1shcake`.

Each app has tests in `<app>/tests/unit/` (unit) and `<app>/tests/integration/` (Selenium/client). See `tests/test_manager.py` for the test framework core.

### Unit test class structure

Unit test files live in `<app>/tests/unit/unit_test_*.py`. The test runner discovers them by glob and instantiates every class it finds. **Do not inherit from `django.test.TestCase`** — just define a plain class.

```python
from tests.test_manager import CobaltTestManagerUnit

class MyFeatureTests:
    def __init__(self, manager: CobaltTestManagerUnit):
        self.manager = manager
        # Create any fixtures needed across all tests in this class

    def test_01_something(self):
        result = do_something()
        self.manager.save_results(
            status=result == expected,          # bool
            test_name="Human-readable name",
            test_description="What this test checks",
            output=f"Got {result!r}, expected {expected!r}",
        )
```

Key rules:
- `__init__` receives the `CobaltTestManagerUnit` instance; store it as `self.manager`.
- Every method whose name starts with `test_` is auto-discovered and run.
- Use `self.manager.save_results()` to record outcomes — no `assert` statements.
- Pre-built users are available as `self.manager.alan`, `.betty`, `.colin`, etc.
- All DB writes are wrapped in a rolled-back transaction, so tests are isolated from the live database.
- Helper functions shared across multiple test files live in `tests/unit/general_test_functions.py`.

### Mocking external APIs in unit tests

Use `unittest.mock.patch.object` as a context manager to patch at the method level rather than at the `requests` level — this is cleaner and avoids token-refresh side effects:

```python
from unittest.mock import patch

def test_something(self):
    xero = XeroApi()
    mock_response = {"Contacts": [{"ContactID": "abc"}]}
    with patch.object(xero, "xero_api_post", return_value=mock_response) as mock_post:
        result = xero.some_method(...)

    # Inspect the payload that was sent
    payload = mock_post.call_args[0][1]
    self.manager.save_results(status=..., ...)
```

For tests that can run both mocked and live (e.g. toggled by a `MOCK_XERO_API` flag), use `contextlib.nullcontext` as the no-op alternative:

```python
from contextlib import nullcontext

def _patch_post(xero, response):
    if MOCK_XERO_API:
        return patch.object(xero, "xero_api_post", return_value=response)
    return nullcontext(None)
```

Tests that inspect `mock.call_args` (payload structure, URL parameters) must always run mocked. Guard them with an early return:

```python
def test_payload_structure(self):
    if not MOCK_XERO_API:
        self.manager.save_results(status=True, test_name="... [SKIPPED]", ...)
        return
    # ... patch and inspect ...
```

### Testing integrations with external services (Xero, Stripe, etc.)

- **Default to mocked.** Tests that hit live external APIs are slow, require credentials, and create persistent data that cannot be rolled back.
- **Use a sandbox/demo account** when live testing is necessary. Never run live API tests against production credentials.
- **Data created via API calls is not rolled back** even though the Django DB transaction is. Live test runs will leave contacts, invoices, or payments in the external system.
- **Document the flag clearly** at the top of the test file, including what credentials or IDs are needed for live mode and what tests will be skipped. See `xero/tests/unit/unit_test_xero_api.py` for the reference implementation of this pattern.

---

## Key Domain Concepts

- **System Number** — the ABF membership number, used as the primary identifier for people throughout the app (not Django's `pk`). Stored on the custom `User` model as `system_number`.
- **Bridge Credits** — an internal virtual currency used for payments within the platform.
- **Membership States** — `CURRENT`, `FUTURE`, `DUE`, `LAPSED`, `ENDED`, `RESIGNED`, `TERMINATED`, `DECEASED`.
- **Auto Pay** — automatic payment of membership fees from Bridge Credits on a scheduled date.
- **Unregistered Users** — people in the system (e.g. contacts imported from clubs) who have not yet created an account. They have a sentinel email `noemail@notset.com`.
- **GLOBAL_ORG** — `"ABF"` — the top-level organisation.
- **does_not_renew** — a membership type flag meaning the membership never expires (lifetime/life member).

---

## Environments

| Name | Hostname |
|---|---|
| Development | `127.0.0.1:8000` |
| Test | test.myabf.com.au |
| UAT | uat.myabf.com.au |
| Production | www.myabf.com.au |

`DISABLE_PLAYPEN=OFF` on non-production environments prevents real emails from being sent. Set `DISABLE_PLAYPEN=ON` only on production.