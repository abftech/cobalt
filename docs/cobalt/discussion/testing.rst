:orphan:

.. image:: ../../images/cobalt.jpg
 :width: 300
 :alt: Cobalt Chemical Symbol

.. image:: ../../images/testing.jpg
 :width: 300
 :alt: Testing

##################
Testing Overview
##################

This page describes the testing strategy for Cobalt. Also see the documentation on building core test data -
:doc:`../reference/test_data`.

*******
Basics
*******
We have a Test environment as well as a User Acceptance Testing (UAT) environment for the
ABF instance of Cobalt (My ABF). Either of these can be used for testing, but generally Test is used for
normal user testing by the core team and UAT is used for a wider group of people. UAT is also a core
part of the release process to check that releases will work in production.

We have three types of automated tests, Unit tests, Integration tests and Smoke tests.

**Unit Tests**
    are shorter, isolated tests that check the internal workings of the code.
    They do not need a Django server in order to run.
**Integration Tests**
    are developing stories. We start by creating a user in chapter 1, in chapter
    4 we create a congress and in chapter 5 the user enters the congress.
    Integration tests need both Stripe and a Django server in order to run.
**Smoke Tests**
    are basically the same as Integration Tests but rather than writing
    code to build them, you write scripts. They shouldn't really be called
    Smoke tests as they have evolved from their initial use.

All tests start with a basic database that has test data loaded (this can be (re-)built by running
`cgit_dev_test_reload_db`. This only needs to be run once. It builds the test database and then takes
a dump of it which the other test scripts restore from each time they run.

Unit tests can be run in any order and do not update the database (this is handled by the test harness,
it just rolls back any changes after each individual test has run).

Integration tests do update the database and need to run in order as do Smoke tests.

Shockingly we have our own test harness, but more on that below.

Tests work off a clean, empty database. Production
isn’t clean nor empty so we need to be careful with
changes that can affect existing production data.

*************
User Testing
*************

* Humans can test in any environment, it doesn’t matter
* UAT is intended for use by people outside the core team, Test is intended to be internal
* Test should always run the code from the develop branch
* Production should always run the code from the master branch with a branch called release/x.x.x holding a point in time version of master
* UAT should run the candidate code for the next release
* All functionality should be supported by automatic test data than can be reset easily
* Humans should do post-install testing on production whenever possible
* Since we don't store anything particularly confidential, we can also test against copies of production data before releasing to production as data is the biggest cause of problems

***************************
Automated Testing - General
***************************

Commands
********

The main commands are:

- **cgit_dev_test_reload_db**
    rebuilds the test database and takes a backup for the other
    scripts to run against. This should be automatically run by the other scripts
    if they detect model changes.
- **cgit_dev_test_all**
    runs all tests. This is the standard command to run.
    The commands below are used more when developing tests.
- **cgit_dev_test_unit**
    runs only the unit tests
- **cgit_dev_test_integration**
    runs only the integration tests. specify --module <classname> to run a
    single test. You will often need to run more than one test as they build upon each other,
    it is easier to comment out the tests you don't want in `tests/test_manager.py`
- **cgit_dev_test_unit**
    runs only the unit tests
    To run the automated tests together you can use `cgit_dev_test_all`.

`cgit_dev_test_all` is intended to be run
as part of the development process and no production release should be performed if any tests
are failing.

Note, all of the sub-scripts to run tests take `--coverage` as a parameter to run with the package
`coverage` but this only really makes sens when running all tests together from `cgit_dev_test_all`
to work out how much of the code we are testing. You don't need to specify this when running
`cgit_dev_test_all` as it handles this automatically.

Automated Testing - Unit
========================

The unit tests are generally short and work at the function level. You can run them with `cgit_dev_test_unit`.

The easiest way to build new tests is to copy existing ones. Unit tests live in `<module>/tests/unit`.

Unit tests are easier to write than integration tests and you are encouraged to write as many as possible.

Unit tests are automatically discovered but can be run in any random order.

Automated Testing - Integration
===============================

There are two basic types of automated tests used:

* Selenium is used to test through the web page
* We also use the Django test client, along with direct model access and Forms to do functional testing.

Both approaches are used together, so we might use Selenium to create something and then access
the model directly to confirm it was successful.

You can run them with `cgit_dev_test_integration`.

The easiest way to build new tests is to copy existing ones.
Integration tests live in `<module>/tests/integration`.

Integration tests must run in order so they are manually configured in `tests/test_manager.py`.

Automated Testing - Smoke
===============================

The Smoke test framework makes developing tests much faster than integration tests
but it is quite limited. Build smoke tests to test for simple things and integration
tests for more complex things.

If you have a situation that smoke tests can't cope with,
consider extending the list of commands that the smoke test harness supports over switching
to an integration test as this will then be available to use in other smoke tests.

Smoke test scripts live in `tests/scripts/test_suite`.

To list the available commands, you can run::

    ./manage.py run_tests_smoke --list

To run a single test you can run::

    cgit_dev_test_smoke --module <filename>

********************
Performance Testing
********************

There are currently over 5,000 people involved in performance testing.

    "Premature optimization is the root of all evil." Sir Tony Hoare

We are also using New Relic for performance monitoring, however at this stage there are very
few problems coming up.

****************
Security Testing
****************

Some of the automated tests focus on specific aspects of security and one module tests for URLs that do not
require authorisation.

************************************************
Why Don't We Use a Recognised Testing Framework?
************************************************

We started out with minimal testing and then added pytest. We quickly hit limitation
with this and ended up building a very simple test framework ourselves.

It is easy to use (copy an example) and produces human readable HTML files that explain what
was tested and what the outcome was. Neither pytest nor unittest can do this.

However, the Cobalt testing framework is fairly brittle and especially subject to problems
when there are changes to the underlying test data or when there are timeout problems.

It might be worth revisiting the decision not to use a recognised test framework at
some point in the future.

