===============
Getting started
===============

Introduction
============

If you are new to audible, this is the place to begin. The goal of this
tutorial is to get you set-up and rolling with audible. I won't go into 
too much detail here, just some important basics.

Hello Library
=============

.. code-block:: python

   import audible
   
   auth = audible.LoginAuthenticator(
       username,
       password,
       locale=country_code,
       register=False)
   
   client = audible.AudibleAPI(auth)
   
   library, _ = client.get("library")
   
   for book in library["items"]:
       print(book)

The example above will get the audible library for the authenticated user and 
the selected marketplace.

Register a device
=================

A device can be registered after a fresh login this way::

   auth.register_device()

.. important::

   Every device registration will add a entry to amazon devices list. So register only 
   when it is necessary. The best way is to save the auth credentials after device 
   registration or deregister device with ``auth.deregister_device()`` before you close 
   your session. 

Load/Save credentials
=====================

To save the auth credentials to file::

    auth.to_file(filename)


And load the credentials from file to reuse it::

    auth = audible.FileAuthenticator(filename)
