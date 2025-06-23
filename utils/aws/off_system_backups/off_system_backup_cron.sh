#!/usr/bin/env bash
#####################################################
# call this from cron to run the off system backups #
#####################################################
SESSION_LOG=/tmp/off_system_backups.log
# This is also used by notifications/management/commands/off_system_backups_email.py

echo "Starting off system backup cron" > $SESSION_LOG

# bashrc isn't run so run it now
source ~/.bashrc

# Get latest code
# git pull origin develop >> $SESSION_LOG 2>&1
git pull origin remediation-part-3 >> $SESSION_LOG 2>&1

# Install Pip packages
pip install -r requirements.txt >> $SESSION_LOG 2>&1

# Change directory
cd utils/aws/off_system_backups || { echo "cd to utils/aws/off_system_backups failed" >> $SESSION_LOG; exit 1; }

# Run it
./off_system_backups.sh>> $SESSION_LOG 2>&1