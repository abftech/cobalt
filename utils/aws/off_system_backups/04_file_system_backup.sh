#!/usr/bin/env bash

##############################################
# Off system backups                         #
#                                            #
# Handle file system backups                 #
#                                            #
##############################################

# Copy file system
# We use rsync as it only copies changes
echo "Starting rsync to copy files..."

if ! rsync \
  -avzr \
  -e "ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i $SSH_KEY_FILE" \
   --progress \
   ec2-user@"$EC2_IP_ADDRESS":/cobalt-media "$FILE_SYSTEM_DIRECTORY"
then
  ./notify.sh error "Error running rsync"
  exit 1
fi

# Dedupe file system to save space
../../tools/replace_duplicates_with_symlinks.sh "$FILE_SYSTEM_DIRECTORY"

# Now create a compressed version of it with date attached
tar -zcvf "$FILE_SYSTEM_DIRECTORY"/backup-$(date '+%Y-%m-%d').tar.gz "$FILE_SYSTEM_DIRECTORY"/cobalt-media

# Keep 3 copies - delete the rest
find "$FILE_SYSTEM_DIRECTORY" -maxdepth 1 -mtime +3 -type f -delete
