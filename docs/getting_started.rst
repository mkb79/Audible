.. _getting_started:


***************
Getting started
***************

Introduction
============

If you are new to audible, this is the place to begin. The goal of this
tutorial is to get you set-up and rolling with audible. I won't go
into too much detail here, just some important basics.


First steps
===========

.. code-block :: python

   import audible
   
   auth = audible.LoginAuthenticator(
       username,
       password,
       locale=marketplace_code,
       register=False)
   
   client = audible.AudibleAPI(auth)
   
   library, raw_resp = client.get(path="library")
   
   for book in library["items"]:
       print(book)

The example above will fetch the audible library for the authenticated user and selected 
marketplace.

A device can be registered after a fresh login this way::

   auth.register_device()

.. important::

   Every device registration will fill a slot on amazon devices list. Please save the auth 
   instance after device registration and reuse it or deregister device before you close 
   your session. 

To save the auth instance to file::

    auth.to_file(filename)

And load the auth instance from file and reuse it::

    auth = audible.FileAuthenticator(filename)
