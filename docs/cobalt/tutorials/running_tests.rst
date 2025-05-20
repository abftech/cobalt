:orphan:

.. image:: ../../images/cobalt.jpg
 :width: 300
 :alt: Cobalt Chemical Symbol

.. image:: ../../images/development.jpg
 :width: 300
 :alt: Coding

===============
Running Tests
===============


.. note::

    This tutorial is designed for a Mac.
    If you are using another operating system and get this to work, please update this document.

Pre-requisites
==============

You need to have your environment already set up. See :doc:`getting_started`

You also need to install the Python packages for development::

    pip install -r requirements-dev.txt

Goals
=====

By the end of this tutorial you will understand:

- The key components of the test framework
- How to run Unit and Integration tests
- How to diagnose when things go wrong

Components
==========================

In order to run the tests you will need to have set up:

- AWS Credentials
- Google Credentials
- Stripe Account

The test harness will start all of the required components.

Stripe
=======

Before you try to run the tests, make sure you have the latest Stripe CLI installed::

    brew upgrade stripe/stripe-cli/stripe

Also, if you haven't used it recently, you will need to log Stripe in::

    stripe login

The test harness will open two windows when it runs, one is the Django server and the other
is the Stripe cli to intercept the call backs. Both of these windows close when the tests finish.
If you need to see errors messages in either of them that disappear too quickly to read then edit
`utils/cgit/tools/test_stripe_short.sh` and comment out the exit at the end.

Selenium
=========

Selenium talks to Chrome to drive the Integration tests (You can use another browser if you like).

You need a version of the Chromedriver that matches your installed browser. Google releases
new versions of Chrome all the time so you will regularly need to run::

    brew update                                                                                                                                                                         ─╯
    brew upgrade chromedriver
    xattr -dr com.apple.quarantine "$(which chromedriver)"

Basic Operation
===============

To run both Unit and Integration tests together::

    cgit_dev_test_all

Common Problems
===============

Database Setup
--------------

The scripts will rebuild the test database if they think it is necessary. You can do this
manually and it is worth trying first if you have any problems::

    cgit_dev_test_reload_db

Note, the database will go 'stale' after a week or so as the closing dates for events will be
passed and tests will fail with nasty looking Selenium errors about items not being found.
Selenium
--------

If you get errors trying to find elements on a page, things such as boolean object has no attribute
.click(), etc, then try running it again, web browsers can be unpredictable.

Running Single Tests
--------------------

When you are developing new tests or debugging a test that is failing, you don't really want to
run every test each time.

You can run the Integration and Unit tests separately::

    cgit_dev_test_unit
    cgit_dev_test_integration

You can also run a single test file for Integration tests::

    cgit_dev_test_integration --module MemberTransfer

Some tests require data created by earlier tests. If you want to run a few tests together but not
the rest of the Integration tests, you can edit `tests/test_manager.py` and comment out the other
tests at the top of the file.

Debugging
---------

You can run::

    cgit_dev_test_integration --debug

This will wait for you to start your IDE to run the tests instead of it starting another window.
You need to point your Django server to the test database and run it on port 8088.

You can also have the code pause allowing you to investigate it's state either from a web browser
or by using `./manage.py shell_plus`. To do this add the following to your test::

    self.manager.sleep()