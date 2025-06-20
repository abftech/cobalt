#!/usr/bin/env bash
##################################################################
#                                                                #
# This sets up the local Cobalt environment.                     #
# This script may need to be changed depending on where the      #
# off system backups are run.                                    #
#                                                                #
# This expects to be run from the utils/aws/off_system_backup    #
# directory.                                                     #
##################################################################

# Set up environment and change to directory
cd
# This will give errors for quotes, we can ignore this
source bin/cobalt.sh