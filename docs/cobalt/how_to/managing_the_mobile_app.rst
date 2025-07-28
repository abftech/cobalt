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

Go to Android Studio -> Settings -> Plugins and add Flutter.