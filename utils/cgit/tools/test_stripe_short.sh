#!/bin/bash

. ~/bin/cobalt.sh
export RDS_DB_NAME=test
stripe listen --forward-to 127.0.0.1:8088/payments/stripe-webhook
exit