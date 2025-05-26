#!/usr/bin/env bash
##############################################
# Off system backups                         #
#                                            #
# Update firewall rule in AWS                #
# so we can connect if local IP had changed  #
##############################################

echo "Updating firewall rule in AWS to we can connect to the database..."

# Run aws command and check return code

echo aws ec2 modify-security-group-rules \
    --group-id sg-e6b3fd98 \
    --security-group-rules SecurityGroupRuleId=sgr-0f0e494ea840a7a52,SecurityGroupRule="{Description='Off Sys Backup',IpProtocol=-1,CidrIpv4=$MY_IP/32}"


if ! aws ec2 modify-security-group-rules \
    --group-id sg-e6b3fd98 \
    --security-group-rules SecurityGroupRuleId=sgr-0f0e494ea840a7a52,SecurityGroupRule="{Description='Off Sys Backup',IpProtocol=-1,CidrIpv4=$MY_IP/32}"
then
  echo "aws ec2 command failed"
  exit 1
fi