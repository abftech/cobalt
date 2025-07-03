#!/bin/bash

. ~/bin/cobalt.sh
utils/cgit/tools/explosion.sh
cat utils/cgit/tools/test.txt
sleep 1
clear
export RDS_DB_NAME=test
coverage run -p manage.py runserver 0.0.0.0:8088 --noreload
exit