#!/usr/bin/env bash
##############################################
# Off system backups                         #
#                                            #
# Set up environment variables               #
#                                            #
##############################################

###################################
# Hard coded values               #
###################################

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
##################################
# AWS dynamic values             #
##################################

# Find the Elastic Beanstalk environment to use
echo ""
echo "Looking for name of Production Elastic Beanstalk environment..."
EB_ENV=$(eb list | grep cobalt-production)
export EB_ENV
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
export RDS_HOSTNAME

# Get the database name
RDS_DB_NAME=$(grep RDS_DB_NAME $ENV_FILE | awk '{print $3}')
export RDS_DB_NAME

# Get the user name
RDS_USERNAME=$(grep RDS_USERNAME $ENV_FILE | awk '{print $3}')
export RDS_USERNAME

# Remove temp file
echo "Deleting temp file..."
rm $ENV_FILE

################################
# IP Addresses                 #
#                              #
# AWS and this host            #
################################

# Get an EC2 instance from the EB environment
echo "Finding an EC2 instance..."
INSTANCE=$(eb list --verbose | grep "$EB_ENV" | awk 'NF>1{print $NF}' | tr -d "'" | tr -d "]" | tr -d "[")
echo "Instance is $INSTANCE"

# Get IP of instance
echo "Getting the IP address of the instance..."
EC2_IP_ADDRESS=$(aws ec2 describe-instances --instance-ids "$INSTANCE" | grep PublicIpAddress | head -1 | awk '{print $2}' | tr -d '",')
export EC2_IP_ADDRESS
echo "IP Address of $EB_ENV is $EC2_IP_ADDRESS"

# Get local IP address
echo "Getting your IPv4 address..."
MY_IP=$(curl -4 ifconfig.co)
export MY_IP

echo "Your IP is $MY_IP"