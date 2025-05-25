#!/usr/bin/env bash

##############################################
# Off system backups                         #
#                                            #
# Handle database backup                     #
#                                            #
##############################################

# Dump file
echo "Running pg_dump to extract the data..."
#pg_dump --exclude-table-data "public.notifications_abstractemail" --exclude-table-data "public.post_office_*" -h "$RDS_HOSTNAME" -p 5432 -d "$RDS_DB_NAME" -U "$RDS_USERNAME" -F c -b -v -f "$DUMP_FILE"
# pg_dump -h "$RDS_HOSTNAME" -p 5432 -d "$RDS_DB_NAME" -U "$RDS_USERNAME" -F c -b -v -f "$DUMP_FILE"

# Run pg_dump and check return code
if ! pg_dump \
             --exclude-table-data "public.notifications_abstractemail" \
             --exclude-table-data "public.post_office_*" \
             -h "$RDS_HOSTNAME" \
             -p 5432 \
             -d "$RDS_DB_NAME" \
             -U "$RDS_USERNAME" \
             -F c -b -v \
             -f "$DUMP_FILE"
then
  echo "Error running pg_dump"
  exit 1
fi

