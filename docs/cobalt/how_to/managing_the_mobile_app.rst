:orphan:

.. image:: ../../images/cobalt.jpg
 :width: 300
 :alt: Cobalt Chemical Symbol

==================================
Managing the Mobile Application
==================================

Cobalt has a mobile application that is used to send notifications
(results and draws) to players. It is written in Flutter and deployed
for Android and iOS.

Development Environment Set Up
==============================

.. warning::
    Flutter and the associated tools change rapidly. These instructions
    may be out of date.

Set Up Code
-----------

Set up the code::

    mkdir cobalt-mobile
    cd cobalt-mobile
    git init
    git remote add origin https://github.com/abftech/cobalt-mobile.git
    git fetch

Install Flutter
---------------

This takes forever.

You will need support for Android and iOS. You can start with iOS and add Android afterwards.

Instructions here: https://docs.flutter.dev/get-started/install/macos/mobile-ios

Instructions for adding iOS are at the bottom of that page.

To install Cocoapods you need to use brew not gem.::

    sudo gem uninstall cocoapods
    brew install cocoapods

I needed to add the SDK command line tools: https://docs.flutter.dev/install/troubleshoot

Once you can run `flutter doctor` without error, you are done.

Open Simulator
---------------

You can open an iOS simulator with::

    open -a Simulator

Android Studio
--------------

Open the project in Android Studio.

Go to **Android Studio** -> **Settings** -> **Plugins** and add Flutter.

You may also need to enable Dart support. Got to **Android Studio** -> **Settings** ->
**Languages and Frameworks** -> **Dart** and tick to enable it.

You will also need to put in the SDK path: ~/Development/flutter/bin/cache/dart-sdk

Updates
-------

If it hasn’t been touched for a while you will probably need to upgrade the package
dependencies. These commands may help::

    flutter pub upgrade
    flutter pub outdated
    flutter pub upgrade --major-versions

Google Firebase Cloud Messaging
===============================

Existing Set Up
---------------

If you are using an existing FCM set up, then you just need the credentials.

Mark Guthrie - *These can be copied from Google Drive*::

    cp -r ~/Library/CloudStorage/GoogleDrive-us@gu3.au/My\ Drive/Work/ABF/MyABF/Bob/ .

New Set Up
----------

If you are setting up a new FCM system and will be using it for Production, be aware
that the release of the client code and server code need to be done together and there
will likely be an outage as clients get updated.

Go to the Firebase Console and create a new project. Call it whatever you like.

Add iOS support and use the bundle ID: au.com.myabf.

Click **Register App** and download GoogleService-info.plist. This needs to go into
`iso/runner`.

Go back to the console and choose **Add App* and add an Android app using the ID: au.com.abf.myabf.

Download google-services.json. This needs to go into `android/app`.

You will also need the server config file. In the Firebase Console, click on the settings wheel and
go to settings and the Service Accounts tab. Generate a new key and download the file that is produced.
This file needs to go in the location specified by the environment variable `GOOGLE_APPLICATION_CREDENTIALS`.



