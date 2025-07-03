#!/bin/bash

. ~/bin/cobalt.sh
export RDS_DB_NAME=test
unset DEBUG_TOOLBAR_ENABLED
# Run with coverage -p stores the data in a different file
coverage run -p ./manage.py runserver 0.0.0.0:8088 --noreload 2>&1 | tee /tmp/test_manager.txt

exit
