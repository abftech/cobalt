#!/bin/bash

# Check stripe session is valid

# Check if we have a session time in the stripe config file
grep test_mode_key_expires_at ~/.config/stripe/config.toml >/dev/null

if [ $? -eq 1 ]
then
  osascript -e 'tell app "System Events" to display dialog "Stripe CLI is not logged in. Run stripe login"'
  exit 1
fi

# Check if session has expired
file_date=$(grep test_mode_key_expires_at ~/.config/stripe/config.toml | awk '{print $3}' | tr -d "'")
current_date=$(date +"%Y-%m-%d")

if [[ "$file_date" < "$current_date" ]]
then
  osascript -e 'tell app "System Events" to display dialog "Stripe CLI login has expired. Run stripe login"'
  exit 1
fi

# All okay, go
. ~/bin/cobalt.sh
export RDS_DB_NAME=test
stripe listen --forward-to 127.0.0.1:8088/payments/stripe-webhook
exit