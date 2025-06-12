#!/usr/bin/env bash
##################################################################
# Take an off system back up for MyABF                           #
#                                                                #
# Requirements                                                   #
# ============                                                   #
#                                                                #
# 1. This needs to be run from its own directory                 #
# 2. AWS token variables need to be set for this to work         #
# 3. Credentials need to be found in ~/.ssh/cobalt.pem           #
#                                                                #
##################################################################

# Set up environment variables
. 01_environment_variables.sh

# Set AWS to allow us access
if ! ./02_update_aws_firewall_rule.sh
then
  ./notify.sh error "Error updating firewall rule"
  exit 1
fi

# Backup database
if ! ./03_database_backup.sh
then
  ./notify.sh error "Error backing up database"
  exit 1
fi

# Backup file system
if ! ./04_file_system_backup.sh
then
  ./notify.sh error "Error backing up file system"
  exit 1
fi


# Test database

# Copy off site

# Notify success
