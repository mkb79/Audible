===============
Getting started
===============

Introduction
============

If you are new to Audible, this is the place to begin. The goal of this tutorial
is to get you set-up and rolling with Audible. I won't go into too much detail
here, just some important basics.

First Authorization
===================

Before you can communicate with the non-publicly Audible Api, you need to
authorize (login) yourself to Audible with your Amazon username and password.
Please make sure to select the correct Audible marketplace. An overview about
all known Audible marketplaces and associated country codes you can find at
:ref:`country_codes`.

.. code-block::

   import audible
   
   auth = audible.LoginAuthenticator(
       USERNAME,
       PASSWORD,
       locale=COUNTRY_CODE
   )

.. note::

   For security reasons you have to solve a Captcha and complete some extra
   steps. Please take a look at the :ref:`authorization` section for more
   information.

.. _hello_library:

Hello Library
=============

After the authorization is successfully completed, you are ready to make your
first API call. To get and print out all books from your Audible library
(sorted by purchase date in descending order) you can do::

   with audible.Client(auth=auth) as client:
       library = client.get(
           "1.0/library",
           num_results=1000,
           response_groups="product_desc, product_attrs",
           sort_by="-PurchaseDate"
       )
       for book in library["items"]:
           print(book)

.. note::

   The information provided by the API depends on the requested `response_groups`.
   The response from the example above are very minimized. Please take a look at
   :http:get:`/1.0/library` for all known `response_groups` and other parameter
   for the library endpoint.

Register an Audible device
==========================

Working with an *authorized only* Client have some limitations. The
authentication data from an authorized Client expires after 60 minutes and
some API requests are forbidden. To deal with these limitations, simply
register a Audible device after an successfully authorization with::

   auth.register_device()

After these step the Client can use a better method of authentication.

.. important::

   Every device registration will be shown on the amazon devices list. So only
   register once and reuse your authentication data or deregister the device
   with ``auth.deregister_device()`` before you close your session.

Reuse authentication data
=========================

You can store your authentication data after an authorization or device
registration with::

   auth.to_file(FILENAME)

And load the data from file to reuse it later with::

   auth = audible.FileAuthenticator(FILENAME)

