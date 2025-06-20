#!/usr/bin/env bash

##############################################
# Off system backups                         #
#                                            #
# Handle database backup                     #
#                                            #
##############################################

printf "Snapshot to use is ${YELLOW}$DB_SNAPSHOT${NC} and new database name is ${YELLOW}$TEMP_DB_SERVER${NC}\n"
printf "Building temporary DB Server from latest snapshot...\n"
aws rds restore-db-instance-from-db-snapshot --db-instance-identifier "$TEMP_DB_SERVER" --db-snapshot-identifier "$DB_SNAPSHOT" --db-instance-class "db.t3.micro"

printf "Waiting for it to be available...\n"
if ! aws rds wait db-instance-available --db-instance-identifier "$TEMP_DB_SERVER"
then
  ./notify.sh error "Error waiting for temp db server to be available"
  exit 1
fi

# Dump file
printf "Running pg_dump to extract the data.\n"
printf "Dump file is ${BLUE}$DUMP_FILE${NC}...\n"

# Run pg_dump and check return code
if ! pg_dump -h "$RDS_HOSTNAME" -p 5432 -d "$RDS_DB_NAME" -U "$RDS_USERNAME" -F c -b -v -f "$DUMP_FILE"

# exclude big tables if you need this quickly. Also add \ at end of line above if you uncomment this
#             --exclude-table-data "public.notifications_abstractemail" \
#             --exclude-table-data "public.post_office_*"

then
  ./notify.sh error "Error running pg_dump"
  exit 1
fi

# Delete temp database - no need to wait for it to finish
printf "Deleting temp database server ${YELLOW}$TEMP_DB_SERVER${NC}...\n"
aws rds delete-db-instance --db-instance-identifier "$TEMP_DB_SERVER" --skip-final-snapshot

# Now create a compressed version of it with date attached
tar -zcvf "$BACKUP_DIR"/prod-db-$(date '+%Y-%m-%d').tar.gz "DUMP_FILE"

# Keep 5 copies - delete the rest
rm -f $(ls -1t "$BACKUP_DIR"/prod-db-*.tar.gz | tail -n +6)