#!/bin/bash

#!/bin/bash

. ~/bin/cobalt.sh
# utils/cgit/tools/explosion.sh
# cat utils/cgit/tools/well.txt
sleep 1
clear
export RDS_DB_NAME=test
stripe listen --forward-to 127.0.0.1:8088/payments/stripe-webhook
exit