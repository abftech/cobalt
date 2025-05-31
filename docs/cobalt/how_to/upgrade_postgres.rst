:orphan:

.. image:: ../../images/cobalt.jpg
 :width: 300
 :alt: Cobalt Chemical Symbol

==================================
How To Upgrade Postgres
==================================

As long as some downtime is acceptable, we can do database upgrades in a relatively
simple way.

Test
====

The Test database serves Test and UAT. Obviously do this one first.

You can do this from the CLI, as it isn't that common, we'll show the AWS Console
method here.

Create New Database Server from Snapshot
-----------------------------------------

Go to RDS, select your database, and go to the **Maintenance and Backups** tab.

.. image:: ../../images/upgrade_postgres/1.png

Find your snapshot and click **Restore**.

.. image:: ../../images/upgrade_postgres/2.png

In **Settings**, give it a name and choose your EC2 instance size.

.. image:: ../../images/upgrade_postgres/3.png

You should be able to keep everything else at the default and click **Restore DB Instance**
at the bottom of the screen.

For small databases it doesn't take long to restore. It will then take a backup and if your
database version is a long way behind it will automatically upgrade it.

You can go into the database and go to the **Logs and events** tab to see what has happened.

.. image:: ../../images/upgrade_postgres/4.png

Upgrade Database Server
-----------------------

If you go to the **Configuration** tab you will see the version of your database server.

.. image:: ../../images/upgrade_postgres/5.png

You can click **Modify** to upgrade the database.

Select the version you would like.

.. image:: ../../images/upgrade_postgres/6.png

You can leave everything else as it is and scroll to the bottom to click **Continue**.

You will be taken to a confirmation screen. Select **Apply immediately** and then
click **Modify DB instance**.

.. image:: ../../images/upgrade_postgres/7.png

*In this case the version was so old that it was automatically upgraded to a supported version
after the restore.*

You can see the whole timeline if you go back to **Logs and events**:

.. image:: ../../images/upgrade_postgres/8.png

