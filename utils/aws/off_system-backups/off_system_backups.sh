#!/usr/bin/env bash
##################################################################
# Take an off system back up for MyABF                           #
##################################################################
# Temp file location
ENV_FILE=/tmp/prod_env

# Dump file location
DUMP_FILE=/tmp/cobalt_prod.dump

# Turn off AWS pagination
export AWS_PAGER=""

# Find the Elastic Beanstalk environment to use
echo ""
echo "Looking for name of Production Elastic Beanstalk environment..."
EB_ENV=$(eb list | grep cobalt-production)
echo "Found $EB_ENV"

# Get the environment variables
echo "Downloading the environment variables..."
eb printenv "$EB_ENV" > $ENV_FILE

echo "Extracting the values needed..."

# Get the production password - store as environment variable for pg_dump
PGPASSWORD=$(grep RDS_PASSWORD $ENV_FILE | awk '{print $3}')
export PGPASSWORD

# Get the database server
RDS_HOSTNAME=$(grep RDS_HOSTNAME $ENV_FILE | awk '{print $3}')

# Get the database name
RDS_DB_NAME=$(grep RDS_DB_NAME $ENV_FILE | awk '{print $3}')

# Get the user name
RDS_USERNAME=$(grep RDS_USERNAME $ENV_FILE | awk '{print $3}')

echo "$RDS_DB_NAME" "$RDS_HOSTNAME" "$PGPASSWORD" "$RDS_USERNAME"

# Remove temp file
rm $ENV_FILE

# Update firewall rule in AWS
# Update the firewall rule so we can connect if local IP had changed
echo "Getting your IP address..."
IP=$(curl -4 ifconfig.co)

echo "Your IP is $IP"

echo "Updating firewall rule in AWS to we can connect to the database..."
aws ec2 modify-security-group-rules \
    --group-id sg-e6b3fd98 \
    --security-group-rules SecurityGroupRuleId=sgr-0f0e494ea840a7a52,SecurityGroupRule="{Description='Off Sys Backup',IpProtocol=-1,CidrIpv4=$IP/32}"

# Dump file
echo "Running pg_dump to extract the data..."
# pg_dump --exclude-table-data "public.notifications_abstractemail" --exclude-table-data "public.post_office_*" -h "$RDS_HOSTNAME" -p 5432 -d "$RDS_DB_NAME" -U "$RDS_USERNAME" -F c -b -v -f "$DUMP_FILE"
pg_dump -h "$RDS_HOSTNAME" -p 5432 -d "$RDS_DB_NAME" -U "$RDS_USERNAME" -F c -b -v -f "$DUMP_FILE"