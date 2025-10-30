#!/bin/bash
# Wrapper to delay starting a job so production doesn't clash with non-production

# If not on production, sleep for 1 - 2 hours before starting
 if [ "$COBALT_HOSTNAME" != "myabf.com.au" ]; then
   MAX_SLEEP_SECONDS=3600
   RANDOM_SECONDS=$(( ( RANDOM % MAX_SLEEP_SECONDS ) + MAX_SLEEP_SECONDS ))
   sleep $RANDOM_SECONDS
fi
$COMMAND

/var/app/current/utils/cron/wrapper.sh $@