#!/bin/bash

# This lets us connect to the file system (NFS/EFS)
yum -y install amazon-efs-utils

# Driver for Postgres - don't seem to be needed by Django except for ./manage.py dbshell
yum -y install postgresql17

# Git
yum -y install git

# Duplicates finder, needed for cleaning up duplicates in Post Office media
yum -y install fdupes