:orphan:

.. image:: ../../images/cobalt.jpg
 :width: 300
 :alt: Cobalt Chemical Symbol

=======================================
How To Upgrade the System for MPC
=======================================

This document is temporary and can be removed once the work has been done on Production.

Steps for Test
==============

#. Install the latest code
#. Ensure MP_USE_DJANGO is set to YES
#. Copy data from Production to the test system using the instructions here: :doc:`load_production_data_into_test`.
#. Run ./manage.py migrate.
#. Convert users: ./manage.py temp_copy_unreg_to_user
#. Run ./manage.py mpc_sync

Steps for Production
====================

Prep
----

#. Before you start, build a new Production environment (cobalt-production-green), point it to a Test database
#. Also build a new SES environment (cobalt-ses-production-blue)
#. **ENSURE THAT THE PRODUCTION STRIPE CREDENTIALS ARE NOT ENTERED**
#. Install the latest code on the new systems and put them into Maintenance Mode
#. Login to both systems
#. Take a copy of `notifications.unregistered_blocked_email`

Upgrade
-------

#. Set number of instances for Production to 1. This will greatly reduce the time to make changes. `eb scale 1 cobalt-production-blue`. This can be done before the change starts.
#. Put Production systems (cobalt-production-blue, cobalt-ses-production-green) into Maintenance Mode and remove the Stripe credentials, keep a copy of these for later.
#. Using another browser/computer check that a normal user cannot login
#. Take a database snapshot. In the AWS Console, go to RDS, Select `production-blue` then **Actions** - **Take Snapshot**
#. Build a new RDS Instance from the snapshot. Click on the snapshot and go to **Actions** - **Restore Snapshot**. Accept all default values except for the engine size which is in **Instance configuration**. Set this to `db.t3.small`. Set `db instance identifier` to `cobalt-production-green`
#. Run migrations. `eb ssh cobalt-production-green`. Set RDS environment variables. Run `./manage.py migrate`
#. Point cobalt-production-green at the new RDS instance. Set **RDS_DB_NAME** to `ebdb`. Set **RDS_HOSTNAME** to the hostname of the new database server (cobalt-production-green). Set **RDS_USERNAME** to `postgres`. Set **RDS_PASSWORD** to the password used by cobalt-production-blue.
#. Do the same for cobalt-ses-production-blue
#. Ensure MP_USE_DJANGO is NOT set. This will take too long. Continue using the MPC for a few days until the sync has run and the data is present.
#. Add production Stripe credentials to cobalt-production-green. NOT to cobalt-ses-production-blue.
#. Change DNS so myabf.com.au and www.myabf.com.au both point at cobalt-production-green
#. Change DNS so ses.myabf.com.au points at cobalt-ses-production-blue
#. Convert users. `eb ssh cobalt-production-green`. Run `./manage.py temp_copy_unreg_to_user`
#. Test
#. Bring systems out of Maintenance Mode
#. Set number of instances for Production to 2. Do this through the AWS console to set min and max.
#. Enter `notifications.unregistered_blocked_email` data back in

Steps for Production - Fail Back
================================

#. Put cobalt-production-green and cobalt-ses-production-blue into maintenance mode
#. Revert DNS changes
#. Take cobalt-production-blue out of Maintenance Mode
#. If the new system was available to users, then check recent activity, especially entries and payments

Post Implementation Steps
=========================

A few days later, tidy up.

Route 53
--------

Delete the DNS entries (if any) for `cobalt-production-blue` and `cobalt-ses-production-green`

Elastic Beanstalk
-----------------

Remove `cobalt-production-blue` and `cobalt-ses-production-green`.

RDS
---

Remove `production-blue`

Rough Timings
==============

=======  ======================
Step     Time
=======  ======================
1        5 mins
2        5 mins
3        5 mins
4        10 mins*
5        20 mins*
6        5 mins
7        5 mins
8        5 mins
9        0 mins
10       2 mins
11       2 mins
12       2 mins
13       10 mins*
14 Test  Unknown, allow 1 hour
15       5 mins
16       5 mins
17       5 mins
=======  ======================

4 - timed at 8 minutes

5 - timed at 14 and 16 minutes

14 - timed at 4 minutes

Outage time excluding testing: **1 hour 31 minutes**

Total outage time: **2 hours 31 minutes**
