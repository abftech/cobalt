---
name: cobalt-batch-command
description: Scaffold a Django management command for Cobalt following the BatchStatus + CobaltLock pattern. Use when creating a new background job, cron task, or management command.
argument-hint: [command-name] [description of what it does]
---

Create a Django management command following the Cobalt batch job pattern exactly.

## File location
`<app>/management/commands/<command_name>.py`

## Required pattern

```python
import logging
import sys

from django.core.management.base import BaseCommand

from utils.models import BatchStatus
from utils.views.cobalt_lock import CobaltLock

logger = logging.getLogger("cobalt")


class Command(BaseCommand):
    help = "<description of what this command does>"

    def handle(self, *args, **options):
        logger.info("<command_name> starting")

        batch = BatchStatus.objects.create(command="<command_name>")
        summary_lines = []

        try:
            lock = CobaltLock("<command_name>", expiry=10)
            if not lock.get_lock():
                logger.info("<command_name> already running (locked), exiting")
                sys.exit(0)

            # --- do work here ---
            # Append human-readable progress to summary_lines as you go, e.g.:
            # summary_lines.append(f"Processed {count} records")

            lock.free_lock()
            lock.delete_lock()

        except Exception as e:
            logger.exception("<command_name> failed with an unhandled exception")
            batch.status = BatchStatus.STATUS_FAILED
            summary_lines.append(f"\nERROR: {e}")
            batch.summary = "\n".join(summary_lines)
            batch.save()
            raise

        batch.status = BatchStatus.STATUS_SUCCESS
        batch.summary = "\n".join(summary_lines)
        batch.save()

        logger.info("<command_name> finished")
```

## Rules
- Always create `BatchStatus` at the start (status defaults to `STATUS_STARTED`).
- Use `CobaltLock` to prevent concurrent runs; `sys.exit(0)` if lock not acquired.
- Accumulate `summary_lines` throughout — join into `batch.summary` at the end.
- The `except` block sets `STATUS_FAILED`, saves summary, then **re-raises** so cron logs see the error.
- On success, set `STATUS_SUCCESS` after releasing the lock.
- Never hardcode environment-specific values — use environment variables.
- If destructive, guard with a check of `COBALT_HOSTNAME` and raise `SuspiciousOperation` if it matches `myabf.com.au` or `www.myabf.com.au`.

## Reference implementation
`organisations/management/commands/auto_pay_batch.py`

Now create a management command for: $ARGUMENTS
