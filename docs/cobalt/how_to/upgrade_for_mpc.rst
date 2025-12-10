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

#. Before you start, build a new Production environment (cobalt-production-green), point it to a Test database
#. Install the latest code on the new system and put it into Maintenance Mode
#. Take a copy of `notifications.unregistered_blocked_email`
#. Put Production system (cobalt-production-blue) into Maintenance Mode
#. Take a database snapshot
#. Build a new RDS Instance from the snapshot
#. Point cobalt-production-green at the new RDS instance
#. Ensure MP_USE_DJANGO is NOT set. This will take too long. Continue using the MPC for a few days until the sync has run and the data is present.
#. Upgrade DNS so myabf.com.au and www.myabf.com.au both point at cobalt-production-green
#. Convert users: ./manage.py temp_copy_unreg_to_user
#. Run ./manage.py mpc_sync
#. Test
#. Bring system out of Maintenance Mode
#. Enter `notifications.unregistered_blocked_email` data back in

Steps for Production - Fail Back
================================

#. Revert DNS changes
#. Take cobalt-production-blue out of Maintenance Mode
#. If the new system was available to users, then check recent activity, especially entries and payments

