#!/usr/bin/env bash
##################################################################
# Take an off system back up for MyABF                           #
#                                                                #
# This needs to be run from its own directory                    #
#                                                                #
# AWS token variables need to be set for this to work            #
#                                                                #
##################################################################

# Set up environment variables
. ./1_environment_variables.sh

# Set AWS to allow us access
if ! ./2_update_aws_firewall_rule.sh
then
  echo "Error updating firewall rule"
  exit 1
fi

# Backup database
if ! ./3_database_backup.sh
then
  echo "Error backing up database"
  exit 1
fi

# Backup file system
