:orphan:

.. image:: ../../images/cobalt.jpg
 :width: 300
 :alt: Cobalt Chemical Symbol

==================================
How To Upgrade Elastic Beanstalk
==================================

From time to time we need to move to a major new version of Elastic Beanstalk
environment. This is best achieved using a Blue/Green pattern where we build
the new environment alongside the existing one and then cut over the DNS to
perform the migration.

Typically you will be upgrading Python as part of this process as well.

We will use Test as the example here, follow the same process for the other
environments. We assume test is currently running on the Elastic Beanstalk environment
cobalt-test-black, and we are going to build cobalt-test-white to sit along side.

Upgrade Development Environment
===============================

Start by installing a new virtual environment for the version of Python you will be using.

e.g.::

    cd MyDirectoryForCobalt
    pyenv install 3.13
    pyenv shell 3.13
    python -V
    (Check it is 3.13)
    python -m venv myenv3.13
    . ./myenv3.13/bin/activate
    cd cobalt
    pip install - r requirements.txt
    pip install - r requirements-dev.txt

You may need to upgrade some packages, but avoid upgrading anything that makes database
changes. You can work this out by using your existing environment to create a test database
`cgit_dev_test_reload_db`. Then point your new Django environment at this and see if it wants
to apply migrations. e.g. `./manage.py migrate`.

It is important that there are no database changes so you can fail back to the old version in the event of
any problems.

Ensure all the tests work before progressing to the next step.

Update Elastic Beanstalk Configuration
=======================================

Edit `.elasticbeanstalk/config.yml` and change the version to be the one you want.

Get Environment Variables
=========================

Run::

    eb printenv cobalt-test-black | tr -d " " | tr "\n" ","

This will give you a comma delimited list of the current variable. It will remove spaces so some minor
editing could be required for email display names etc. It will also replace the AWS_ACCESS_KEY_ID with
stars so you will need to get that directly from the AWS Console.

Create Environment
===================

Run `eb create` and give it the environment variables that you just extracted::

    eb create cobalt-test-white --keyname cobalt --envvars API_KEY_PREFIX=test_,etc,etc

If you want to specify other parameters you can look them up. For example -i t3.medium will specify the
EC2 server size.

DNS
===

Create a new DNS name to point to your environment. Just use the AWS Route 53 console for this.

.. important::
    If you change production, remember to change both myabf.com.au and www.myabf.com.au

Testing
========

In this example, we used the same database for both environments. If you want to do a lot of testing but still
need the old system available, you can create a new database.

Git Considerations
==================

There will typically only be one or two file changes required, but these need to be kept away from
the code that is being released to the existing servers. The main changes are to `config.yml` and
possibly `requirements.txt`. If you are unlucky you may need to upgrade packages and make code changes.