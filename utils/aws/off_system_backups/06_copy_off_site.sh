#!/usr/bin/env bash
##############################################
# Off system backups                         #
#                                            #
# Copy data off site                         #
##############################################

LATEST_DB=$(ls -rt "$DUMP_FILE"* | tail -n 1)
LATEST_FILE_SYSTEM=$(ls -rt "$FILE_SYSTEM_DIRECTORY"/*.tar.gz | tail -n 1)

if ! aws s3 --profile backblaze cp $"$LATEST_DB" s3://abf-offsite-backups
then
  ./notify.sh error "Error copying DB file to BackBlaze"
  exit 1
fi

if ! aws s3 --profile backblaze cp $"$LATEST_FILE_SYSTEM" s3://abf-offsite-backups
then
  ./notify.sh error "Error copying DB file to BackBlaze"
  exit 1
fi

