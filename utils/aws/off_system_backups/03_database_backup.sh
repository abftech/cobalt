#!/usr/bin/env bash
##############################################
# Off system backups                         #
#                                            #
# Handle database backup                     #
#                                            #
##############################################

# Check if the temp db is there, probably from an earlier problem
EXISTING_INSTANCE=$(aws rds describe-db-instances \
    --query 'DBInstances[*].[DBInstanceIdentifier]' \
    --filters Name=db-instance-id,Values="$TEMP_DB_SERVER" \
    --output text \
    )

if [ -z "$EXISTING_INSTANCE" ]
then
    printf "Temporary DB server $TEMP_DB_SERVER does not exist\n"
else
    printf "Temporary DB server ${YELLOW}$TEMP_DB_SERVER${NC}, already exists. Removing it.\n"
    aws rds delete-db-instance --db-instance-identifier "$TEMP_DB_SERVER" --skip-final-snapshot

    printf "Waiting for ${YELLOW}$TEMP_DB_SERVER${NC} to be deleted...\n"
    if ! aws rds wait db-instance-deleted --db-instance-identifier "$TEMP_DB_SERVER"
    then
      ./notify.sh error "Error waiting for temp db server to be available"
      exit 1
    fi

fi

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

# There is no point compressing the back up, it stays the same size, so just copy it
# The 05_check_database.sh will delete the backup when it finishes
if ! cp "$DUMP_FILE" "$DUMP_FILE".$(date '+%Y-%m-%d')
then
  ./notify.sh error "Error moving database file"
  exit 1
fi

# Keep 3 copies - delete the rest
find "$BACKUP_DIR" -maxdepth 1 -mtime +3 -type f -delete