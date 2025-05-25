#!/usr/bin/env bash

##############################################
# Off system backups                         #
#                                            #
# Handle file system backups                 #
#                                            #
##############################################

# Copy file system
# We use rsync as it only copies changes
rsync \
  -avzr \
  -e "ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i ~/.ssh/cobalt.pem" \
   --progress \
   ec2-user@3.104.63.68:/cobalt-media /tmp/white