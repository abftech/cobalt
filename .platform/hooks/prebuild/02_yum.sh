#!/bin/bash

# This lets us connect to the file system (NFS/EFS)
yum -y install amazon-efs-utils

# Driver for Postgres
yum -y install postgresql.x86_64

# Git
yum -y install git

# Duplicates finder, needed for cleaning up duplicates in Post Office media
yum -y install fdupes