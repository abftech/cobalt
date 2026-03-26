---
name: cobalt-django-shell
description: >-
  Set up a local Django shell or manage.py session connected to the Cobalt test
  database. Use whenever the user wants to run manage.py locally against real data,
  open the Django shell against the test DB, run migrations locally, or run tests
  against the real database.
argument-hint: [manage.py command to run]
---

To run `manage.py` commands against the test database locally:

```bash
source ~/bin/cobalt-common-variables.env   # loads AWS credentials and all required env vars
export RDS_DB_NAME=cobalttestwhite         # point at the test DB
python manage.py $ARGUMENTS
```

## Rules
- `cobalttestwhite` is the test database — it is **not** production data and can be freely read and written to.
- **Never** set `RDS_DB_NAME=cobalt` — that is the production database.
- The env file provides: `AWS_REGION_NAME`, `RDS_HOSTNAME`, `RDS_USERNAME`, `RDS_PASSWORD`, and other required variables.
