:orphan:

.. image:: ../../images/cobalt.jpg
 :width: 300
 :alt: Cobalt Chemical Symbol

.. image:: ../../images/aws.png
 :width: 300
 :alt: Amazon Web Services

#######################
Backups Overview
#######################

This page relates only to the ABF production version of Cobalt.

Basic Backups
#############

We use AWS Relational Database Service (RDS) for our databases.
This is a fully managed service and handles the basic housekeeping
that we need to perform. Full backups (RDS calls them snapshots) are taken each day at about 2:30am.
They are retained for 14 days in production and 7 days for the other environments.

Snapshots can be taken manually, and it recommended that this happens for any major release.

Taking a snapshot prevents database updates at that time and can take time if the database is large.

Basic Restores
##############

You can restore a snapshot from the RDS management console. It will be given a new name and you will need
to point the associated Django Elastic Beanstalk environment at the new database in order to use it.

Additional Off System Backups
#############################

While it is unlikely that anything will go wrong with RDS itself, it is possible for other factors to
affect our database. For example, failure to pay the bill would result in the account being shutdown or
human error could cause the production database and all of its snapshots to be deleted when the
intention was to remove UAT.

For this reason we have an off-system backup which runs daily. This is not without risk as it
needs to access production data and systems in order to copy the data. It also requires
maintenance and testing. The IT equivalent of the medical joke "The operation was successful,
but the patient died" is "The backups worked perfectly, it
was the restores that had problems." For that reason, as well as copying the data we
also restore and test it
each time.

As of 2025, the backup process takes a couple of hours. During that time many things could happen
as the database is not locked to prevent updates.
For example, we could backup the payments tables, recording a balance for a user of $75. Then before
we backup the events tables, they enter an event and their balance is now $20. If we restore from
this backup, they will have been given free entry to the event because we will restore their
balance to $75 but also keep the entry.
It is actually a lot worse than this as we can have integrity issues with foreign keys.

In order to address this, we don't backup from the live database. Instead we use a snapshot taken
by RDS every day, and build a new temporary database server that has no users, and we create
the backup from that.

How It Works
============

The code lives in `utils/aws/off_system_backups`. It can run pretty much anywhere, but needs
a copy of the cobalt code. It needs to run after the RDS snapshot has been taken.

Setting Up on Lightsail
========================

Here are the steps to set up the off system backups on AWS Lightsail. Lightsail is an easy
way to set up an EC2 instance that you can access remotely.

Lightsail Instance
------------------

1. Go to the AWS Lightsail Console
2. Create a new instance. Choose **Linux** -> **OS Only** -> **Amazon Linux 2023**.
3. Choose **Dual Stack**.
4. 2GB is probably enough.
5. Give it a name and create it.

Connect Over SSH
----------------

The Lightsail web based client is pretty awful, you are better connecting over ssh so you
can cut and paste easily.

Go to your instance and into the **Connect** tab. Download the default key and move it to
.ssh with a better name. Note the IP address.

Now you should be able to connect, e.g.::

    ssh -i ~/.ssh/cobalt-lightsail.pem ec2-user@3.106.143.77

    The authenticity of host '3.106.143.77 (3.106.143.77)' can't be established.
    ED25519 key fingerprint is SHA256:nsJIr9yMR2rproGtbH0OsmqeTkGer69KNs+/QRZFaWk.
    This key is not known by any other names.
    Are you sure you want to continue connecting (yes/no/[fingerprint])? yes
    Warning: Permanently added '3.106.143.77' (ED25519) to the list of known hosts.
       ,     #_
       ~\_  ####_        Amazon Linux 2023
      ~~  \_#####\
      ~~     \###|
      ~~       \#/ ___   https://aws.amazon.com/linux/amazon-linux-2023
       ~~       V~' '->
        ~~~         /
          ~~._.   _/
             _/ _/
           _/m/'
    Last login: Fri Jun 20 07:20:34 2025 from 54.240.194.193
    [ec2-user@ip-172-26-11-153 ~]$

Install Postgres
----------------

Install the version of Postgres that you want. For example::

    sudo yum install postgresql17-server.x86_64

You can find the different versions::

    sudo yum list | grep postgr

Configure Postgres
------------------

Initialise Postgres by running::

    sudo postgresql-setup initdb --unit postgresql
     * Initializing database in '/var/lib/pgsql/data'
     * Initialized, logs are in /var/lib/pgsql/initdb_postgresql.log

Now start it::

    sudo systemctl start postgresql

If there are problems have a look at what the issue was::

    systemctl status postgresql.service

Once it is working, get it to start automatically::

    sudo systemctl enable postgresql

Check you can connect to Postgres::

    sudo -u postgres psql
    psql (17.5)
    Type "help" for help.

    postgres=#

While you are working with Postgres, lets add a couple of other things::

    sudo -u postgres createuser -s ec2-user
    sudo -u postgres createdb ec2-user

    sudo -u postgres psql
        psql (17.5)
        Type "help" for help.

        postgres=# ALTER USER "ec2-user" WITH SUPERUSER;
        postgres=# create user cobalt with encrypted password 'F1shcake';

Install Python
--------------

At the time of writing, we were using Python 3.13, but only 3.12 was easily available on
Lightsail. It is unlikely to make much difference for the off system backups.

To see the available versions of python, run::

    sudo yum list | grep python

To install Python 3.12, run::

    sudo yum install python3.12.x86_64

You may need to find where Python has been installed. You can find this by using RPM. e.g.
for the version we just installed::

    rpm -ql python3.12.x86_64

    /usr/bin/pydoc3.12
    /usr/bin/python3.12
    /usr/lib/.build-id
    /usr/lib/.build-id/69
    /usr/lib/.build-id/69/6ecd3c99623b75e63f0fd494e0edf164ba485b
    /usr/share/doc/python3.12
    /usr/share/doc/python3.12/README.rst
    /usr/share/man/man1/python3.12.1.gz

So we want to use `/usr/bin/python3.12`.

Install Git
-----------

Git isn't installed by default so run::

    sudo yum install git

Directory and Git
-----------------

Standard set up for Cobalt::

    # Create a directory and use it
    mkdir c2; cd c2

    # Use the python from above to build a virtual environment.
    # This will need to upgraded when we upgrade Python
    /usr/bin/python3.12 -m venv myenv

    # activate it - we need it in the next step
    . ./myenv/bin/activate

    mkdir cobalt; cd cobalt

    # Open Source so we don't need git credentials to get the code
    git init
    git remote add origin https://github.com/abftech/cobalt.git
    git config pull.rebase false

    # Use develop as our reference branch
    git checkout -b develop
    git pull origin develop

SSH Key
-------

Rsync needs the ssh key for Cobalt. Copy this from your environment into Lightsail, e.g.::

    scp -i ~/.ssh/cobalt-lightsail.pem ~/.ssh/cobalt.pem ec2-user@3.106.143.77:/home/ec2-user/.ssh/cobalt.pem

Then log back into the Lightsail instance and change the permissions::

    chmod 600 ~/.ssh/cobalt.pem

AWS and EB CLI
--------------

We need both AWS CLIs, the AWS CLI is already installed, but to install the EB CLI run::

    pip3 install awsebcli

You will need credentials for this environment. Go to the AWS console and into IAM and
create a set of credentials for the user off-system-backups. If old credentials exist, delete
them.

Create credentials for CLI use.

Add these to the bottom of `~/.bashrc`::

    export AWS_ACCESS_KEY_ID=*************
    export AWS_SECRET_ACCESS_KEY=****************

Also add::
    export AWS_REGION_NAME=ap-southeast-2

You will need some other environment variables::

    export AWS_SES_CONFIGURATION_SET=cobalt-test
    export AWS_SES_REGION_ENDPOINT=email.ap-southeast-2.amazonaws.com
    export RDS_DB_NAME=cobalt
    export RDS_HOSTNAME=127.0.0.1
    export RDS_PORT=5432
    export RDS_USERNAME=cobalt
    export RDS_PASSWORD=F1shcake

You can also add activation of the virtual environment and changing into the
directory.::

    cd c2
    source ./myenv/bin/activate
    cd cobalt

Exit the session and login again to re-run `.bashrc`.

Now run::

    eb init

Activation File
---------------

This one is a bit lazy, but it makes the off system backup structure match this author's
development environment.

Run::

    cd # make sure you are in the home directory
    mkdir bin; cd bin
    cat << EOF > cobalt.sh
    #!/usr/bin/env bash
    source ~/.bashrc
    EOF
    chmod 755 cobalt.sh

Add Disk
--------

Lightsail doesn't come with much disk space so we need to add some more.

From the Lightsail console select your instance go to **Storage** add some storage (256GB should be okay). Connect
this to your instance.

Now ssh into the machine and become root (sudo -s).

Show the disks::

    # lsblk
    NAME          MAJ:MIN RM  SIZE RO TYPE MOUNTPOINTS
    nvme0n1       259:0    0   60G  0 disk
    ├─nvme0n1p1   259:1    0   60G  0 part /
    ├─nvme0n1p127 259:2    0    1M  0 part
    └─nvme0n1p128 259:3    0   10M  0 part /boot/efi
    nvme1n1       259:4    0  256G  0 disk

Our new disk is the bottom one (256GB).

It is an unformatted data disk::

    # file -s /dev/nvme1n1
    /dev/nvme1n1: data

Format it::

    # mkfs -t xfs /dev/nvme1n1
    meta-data=/dev/nvme1n1           isize=512    agcount=16, agsize=4194304 blks
             =                       sectsz=512   attr=2, projid32bit=1
             =                       crc=1        finobt=1, sparse=1, rmapbt=0
             =                       reflink=1    bigtime=1 inobtcount=1
    data     =                       bsize=4096   blocks=67108864, imaxpct=25
             =                       sunit=1      swidth=1 blks
    naming   =version 2              bsize=4096   ascii-ci=0, ftype=1
    log      =internal log           bsize=4096   blocks=32768, version=2
             =                       sectsz=512   sunit=1 blks, lazy-count=1
    realtime =none                   extsz=4096   blocks=0, rtextents=0

Create mount point::

    cd /home/ec2-user
    mkdir abf_backup
    chmod 777 abf_backup
    chown ec2-user abf_backup
    chgrp ec2-user abf_backup

Mount it and ensure it is mounted every time::

    mount /dev/nvme1n1 abf_backup/
    vi /etc/fstab

    # Add to end (previous lines look different, don't worry):
    /dev/nvme1n1 /home/ec2-user/abf_backup/ xfs defaults,nofail 0 2

Reboot your instance and check the file system gets mounted.

Setup Cron
----------

Cron isn't installed by default, you need to run::

    sudo yum install cronie cronie-anacron

    sudo systemctl enable crond.service
    sudo systemctl start crond.service

Check it is working::

    sudo systemctl status crond.service

Now you can add the entry to cron. You need to check when the RDS snapshot is taken and
add a little time on to that. Currently (2025), the entry is::

    crontab -e
    30 16 * * * <path to cobalt>/utils/aws/off_system_backups/off_system_backup_cron.sh

S3 and BackBlaze Setup
======================

We use two "AWS" profiles for S3 to copy files between AWS S3 and BackBlaze, which implements the same
API. One profile is for S3, the other is for BackBlaze.

Set up the two profiles::

    aws configure --profile s3
    aws configure --profile b2

Put in the details for S3 and BackBlaze. You will need to create keys in both systems if you don't already have them.

After this ~/.aws/config should look like, you will need to manually add the endpoint_url line::

    [profile b2]
    region = us-east-005
    endpoint_url = https://s3.us-east-005.backblazeb2.com
    [profile s3]
    region = ap-southeast-2


Off System Restores
===================

TBA