#!/usr/bin/env bash
##############################################
# Off system backups                         #
#                                            #
# Copy data off site                         #
##############################################

# Copy the S3 files to BackBlaze
# Here is what it does:
# - list all of the objects in S3 that have changed in the last week,
# - the output is in Json so we pipe this through jq to get the full path and file name
# - then we loop over the filenames that we get and use the S3 profile to read the file and output to stdin (-),
# - we pipe that into another aws command that uses the BackBlaze profile to connect to there and read from stdin (-)
SINCE=$(date --date '-1 weeks' +%F 2>/dev/null)
echo "Copying files that have changed in the last week from S3 to BackBlaze"
aws --profile s3 s3api list-objects-v2 --bucket diamond-production-media-bucket  --query 'Contents[?LastModified > `'"$SINCE"'`]'| jq '.[] | .Key' | while read -r filename ; do
  filename=$(echo "$filename" | tr -d '"')
  echo "Copying $filename..."
  aws --profile s3 s3 cp s3://diamond-production-media-bucket/"$filename" - | aws --profile b2 s3 cp - s3://hydrabuddy-production/"$filename"
done

# Copy the database file using today's date
echo "Copying database archive to BackBlaze"
today=$(date '+%Y-%m-%d')
aws --profile b2 s3 cp /tmp/production.sql s3://hydrabuddy-production/database_backups/production-"$today".sql