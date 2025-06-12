#!/usr/bin/env bash

##############################################
# Off system backups                         #
#                                            #
# Handle database backup                     #
#                                            #
##############################################

echo "Building temporary DB Server from latest snapshot..."
aws rds restore-db-instance-from-db-snapshot --db-instance-identifier "$TEMP_DB_SERVER" --db-snapshot-identifier "$DB_SNAPSHOT" --db-instance-class "db.t3.micro"

echo "Waiting for it to be available..."
if ! aws rds wait db-instance-available --db-instance-identifier "$TEMP_DB_SERVER"
then
  ./notify.sh "Error waiting for temp db server to be available"
  exit 1
fi

# Dump file
echo "Running pg_dump to extract the data..."

# Run pg_dump and check return code
if ! pg_dump -h "$RDS_HOSTNAME" -p 5432 -d "$RDS_DB_NAME" -U "$RDS_USERNAME" -F c -b -v -f "$DUMP_FILE" \
             --exclude-table-data "public.notifications_abstractemail" \
             --exclude-table-data "public.post_office_*"

then
  ./notify.sh "Error running pg_dump"
  exit 1
fi

# Delete temp database
echo "Deleting temp database $TEMP_DB_SERVER"
aws rds delete-db-instance --db-instance-identifier "$TEMP_DB_SERVER" --skip-final-snapshot
