#!/usr/bin/env bash
##################################################################
#                                                                #
# Notify those interested about success or failure               #
#                                                                #
##################################################################

echo "$*"

# Get variables, we expect to get status (success/error) and a message
STATUS=$1; shift
MESSAGE=$*

# Set up environment
. ./cobalt.sh

# allow emails to be sent
export DISABLE_PLAYPEN=ON

# Send email
./manage.py off_system_backups_email --subject="$MESSAGE" --status="$STATUS"