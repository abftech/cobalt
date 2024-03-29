:orphan:

.. image:: ../../images/cobalt.jpg
 :width: 300
 :alt: Cobalt Chemical Symbol

:doc:`../how_to/using_references`

==========================
Organisations Application
==========================

.. note::
    This page has the documentation on how to use this application
    (externally provided APIs etc). If you are looking for
    information on how it works internally, you can find that in :doc:`./organisations_support`.


--------------
Module Purpose
--------------

Account handles things relating to User accounts such as profiles and settings.
There are multiple user types to support the need to deal with users who have not
registered for the system as well as real, registered users.

--------------
External Usage
--------------

Organisations within Cobalt refers to Clubs, State
Bodies and the Governing Body, although the majority
of the module is concerned with managing Clubs.

Organisations are similar to Members (Users) in that
they can interact with other entities within the
system for payments, settlements etc.

For the ABF we have the concept of State Bodies which
have a level of oversight of clubs within their
state. If this is not required for other users of
Cobalt it should be possible to ignore it and just
use the higher level administrative functions.

Each club has a state and each state has a single
governing (state) body. Cobalt expects to find the
parent of a club (state body) by looking for the
Organisation that has a type of State and a state of
the same state as the club. If more than one state
body is found for a state then Cobalt will throw a
ConfigurationError.

Relationship to Members
=======================

Members are associated with a club through the
MemberOrganisation model. A member can join more
than one club but can only have one "Home Club".
Home Clubs are used for calculating fees payable
to the higher state and national bodies by the clubs
on behalf of their members.

RBAC
====

There are too many clubs to allow a haphazard
approach to handling RBAC rules. All RBAC rules
for clubs are generated by the system and a
standard structure is assumed. It is generally
a bad idea to manually change this structure
unless something has gone wrong, however the content
of the RBAC groups (who is in which group) is
safe to change.

As more functionality is added over time it will be
necessary to update the RBAC roles that the club
RBAC structure has to support. For this reason we
use a dictionary to control the rules that should be
in place.

Organisations.models has a variable to control this
**ORGS_RBAC_GROUPS_AND_ROLES**. This contains a mapping
of group name to RBAC role. e.g. "managers" to "orgs.edit".

RBAC - Simple vs Advanced
-------------------------

Most clubs only want to worry about a small number of
people having access to everything, while some clubs (especially
the larger ones) need a more granular approach so that
they can have staff with different levels of access.

Cobalt supports a simple and an advanced model for this.

* **Simple** - one RBAC group is created with all roles.
* **Advanced** multiple RBAC groups are used with one per role.

RBAC Generated Groups
---------------------

Cobalt generates RBAC groups as follows::

    rbac.orgs.clubs.generated.<state>.<org.id>.<something>

* *state* is the state of the club (lowercase)
* *org.id* is the primary key of the club (we cannot use name as this can be changed)
* *something* depends upon whether this a basic or advanced configuration.

For example, for a basic RBAC configuration we might have::

    rbac.orgs.clubs.generated.act.153.basic

This would contain all of the roles currently in play for a club,
and the associated users.

For an advanced configuration we might have::

    rbac.orgs.clubs.generated.vic.14.managers
    rbac.orgs.clubs.generated.vic.14.directors
    rbac.orgs.clubs.generated.vic.14.payments_view
    rbac.orgs.clubs.generated.vic.14.payments_update

These would each have individual roles and users.

Updating the RBAC Structure
---------------------------

A management script runs each time the application is deployed
and checks if the right groups are present. It assumes that a
basic configuration will have a group called basic, otherwise
it is an advanced configuration.

The script will add any missing groups to clubs that do not
have them. It does this by referring to the variable described above:
**ORGS_RBAC_GROUPS_AND_ROLES**.

It will not remove any additional groups.

Group Membership
----------------

Membership of the different groups is handled by the Club
Admin functions, there should be no need to directly access
RBAC to handle this and it is discouraged to do so.

Admin Roles
-----------

The RBAC admin tree has a corresponding structure with::

    admin.clubs.<state>.<club.id>

This will initially contain the Club Secretary when the
club is first set up, but they can subsequently control the
membership of this group. This provides explicit administrators
per club.

In addition, state bodies can make changes to clubs in their
state if they have the role::

    orgs.state.<state.id>.edit

As a final step, global administrators can change any club's
details if they have the role::

    orgs.admin.edit