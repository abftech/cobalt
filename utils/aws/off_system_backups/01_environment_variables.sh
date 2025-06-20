#!/usr/bin/env bash
##############################################
# Off system backups                         #
#                                            #
# Set up environment variables               #
#                                            #
##############################################

###############################
# Colours for terminal output #
###############################
export RED='\033[0;31m'
export BLUE='\033[0;34m'
export YELLOW='\033[0;33m'
export NC='\033[0m' # No Color

###################################
# Hard coded values               #
###################################
# AWS Name for the database - not the hostname
DB_NAME=cobalt-production

# Turn off AWS pagination
export AWS_PAGER=""

# Location for backup files
export BACKUP_DIR=~/abf_backup

# Dump file location
export DUMP_FILE=$BACKUP_DIR/cobalt_prod.dump

# File system location
export FILE_SYSTEM_DIRECTORY=$BACKUP_DIR/media

# Create directories if not present
mkdir -p $FILE_SYSTEM_DIRECTORY

# Security
export SSH_KEY_FILE=~/.ssh/cobalt.pem

# Temp file location
ENV_FILE=/tmp/prod_env

# Temp DB instance - we create this to take the dump from so it doesn't change as we do the backup
export TEMP_DB_SERVER=offsystem-temp

##################################
# AWS dynamic values             #
##################################

# Find the Elastic Beanstalk environment to use
printf "\nLooking for name of Production Elastic Beanstalk environment...\n"
EB_ENV=$(eb list | grep cobalt-production)
export EB_ENV
printf "Found ${YELLOW}$EB_ENV${NC}\n"

# Get the environment variables
printf "Downloading the environment variables...\n"
eb printenv "$EB_ENV" > $ENV_FILE

printf "Extracting the values needed...\n"

# Get the production password - store as environment variable for pg_dump
PGPASSWORD=$(grep RDS_PASSWORD $ENV_FILE | awk '{print $3}')
export PGPASSWORD

# Get the database server
RDS_HOSTNAME=$(grep RDS_HOSTNAME $ENV_FILE | awk '{print $3}')

# We will run up a new server from the latest snapshot, so change this name to be that
# e.g. we get cobalt-production.fish.aws.com but we want tempdb.fish.aws.com

RDS_HOSTNAME=$(echo "$RDS_HOSTNAME" | sed "s/$DB_NAME/$TEMP_DB_SERVER/")
export RDS_HOSTNAME

# Get the database name
RDS_DB_NAME=$(grep RDS_DB_NAME $ENV_FILE | awk '{print $3}')
export RDS_DB_NAME

# Get the user name
RDS_USERNAME=$(grep RDS_USERNAME $ENV_FILE | awk '{print $3}')
export RDS_USERNAME

# Remove temp file
printf "Deleting temp file...\n"
rm $ENV_FILE

################################
# IP Addresses                 #
#                              #
# AWS and this host            #
################################

# Get an EC2 instance from the EB environment
printf "Finding an EC2 instance...\n"
INSTANCE=$(eb list --verbose | grep "$EB_ENV" | awk 'NF>1{print $NF}' | tr -d "'" | tr -d "]" | tr -d "[")
printf "Instance is ${BLUE}$INSTANCE${NC}\n"

# Get IP of instance
printf "Getting the IP address of the instance...\n"
EC2_IP_ADDRESS=$(aws ec2 describe-instances --instance-ids "$INSTANCE" | grep PublicIpAddress | head -1 | awk '{print $2}' | tr -d '",')
export EC2_IP_ADDRESS
printf "IP Address of ${BLUE}$EB_ENV${NC} is ${YELLOW}$EC2_IP_ADDRESS${NC}\n"

# Get local IP address
printf "Getting your IPv4 address...\n"
MY_IP=$(curl -4 ifconfig.co 2>/dev/null)
export MY_IP

printf "Your IP is ${YELLOW}$MY_IP${NC}\n"

####################################
# Latest snapshot                  #
####################################
printf "Getting database snapshot name...\n"
DB_SNAPSHOT=$(aws rds describe-db-snapshots \
  --query="max_by(DBSnapshots, &SnapshotCreateTime).DBSnapshotIdentifier" --db-instance-identifier $DB_NAME --output text)

export DB_SNAPSHOT

printf "Latest database snapshot for ${RED}$DB_NAME${NC} is ${YELLOW}$DB_SNAPSHOT${NC}\n\n"