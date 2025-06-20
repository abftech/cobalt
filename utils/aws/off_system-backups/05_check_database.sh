#!/usr/bin/env bash
##############################################
# Off system backups                         #
#                                            #
# Restore database and check it works        #
##############################################
# local database
LOCAL_DB_NAME=prod_load

# Load the database
printf "Loading database, dropping old DB ${RED}$LOCAL_DB_NAME${NC}..."
cat << EOF > /tmp/drop_db_prod_copy
\c postgres
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = '$LOCAL_DB_NAME';
drop database IF EXISTS $LOCAL_DB_NAME;
create database $LOCAL_DB_NAME with owner cobalt;
EOF

if ! psql </tmp/drop_db_prod_copy
then
  ./notify.sh error "Error dropping and recreating local database"
  exit 1
fi

# Load the database
printf "Loading the data, this will take a while...\n"
if ! pg_restore -h localhost -p 5432 -U postgres -d $LOCAL_DB_NAME --no-owner --no-privileges --role=cobalt -v "$DUMP_FILE"
then
  ./notify.sh error "Error running pg_restore locally"
fi

###############################################################################################
# Sanitise the data - we do this through Cobalt.                                              #
# Note - this is just for the data loaded in local Postgres, the dump file is not touched     #
###############################################################################################

# Set up environment
. ./cobalt.sh

# sanitise data
./manage.py sanitise_production_data_for_testing
