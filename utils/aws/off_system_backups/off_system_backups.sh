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
# 4. It requires a full install of cobalt (files from git)       #
# 5. It requires Postgres to be available                        #
# 6. It requires eb and aws CLIs to be set up and working        #
#                                                                #
##################################################################

# Set up environment variables
. 01_environment_variables.sh

# Set AWS to allow us access
if ! ./02_update_aws_firewall_rule.sh
then
  exit 1
fi

# Backup database
if ! ./03_database_backup.sh
then
  exit 1
fi

# Backup file system
if ! ./04_file_system_backup.sh
then
  exit 1
fi

# Test database
if ! ./05_check_database.sh
then
  exit 1
fi

# Copy off site
if ! ./06_copy_off_site.sh
then
  exit 1
fi

# Notify success
./notify.sh success "Off system backups were successful"
