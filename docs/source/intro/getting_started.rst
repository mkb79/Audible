===============
Getting started
===============

Introduction
============

If you are new to Audible, this is the place to begin. The goal of this tutorial
is to get you set-up and rolling with Audible. I won't go into too much detail
here, just some important basics.

First Audible device
====================

Before you can communicate with the non-public Audible Api, you need to
authorize (login) yourself to Amazon (or Audible) and register a new "virtual"
Audible device. Please make sure to select the correct Audible marketplace.
An overview about all known Audible marketplaces and associated country codes
be found at :ref:`country_codes`.

.. code-block::

   import audible

   # Authorize and register in one step
   auth = audible.Authenticator.from_login(
       USERNAME,
       PASSWORD,
       locale=COUNTRY_CODE,
       with_username=False
   )

   # Save credentials to file
   auth.to_file(FILENAME)

.. important::

   Every device registration will be shown on the Amazon devices list. So only
   register once and reuse your authentication data or deregister the device
   with ``auth.deregister_device()`` before you close your session.

.. note::

   If you have activated 2-factor-authentication for your Amazon account, you
   can append the current OTP to your password. This eliminates the need for a
   new OTP prompt.

.. note::

   Set `with_username=True` to login with your pre-Amazon account (for US, UK or
   DE marketplace only).

.. note::

   For security reasons in some cases you have to solve a Captcha and complete
   some extra steps. Please take a look at the :ref:`authorization` section for
   more information.

.. _hello_library:

Hello Library
=============

After the device creation was successfully completed, you are ready to make
your first API call. To fetch and print out all books from your Audible library
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

   The information returned by the API depends on the requested `response_groups`.
   The response for the example above are very minimized. Please take a look at
   :http:get:`/1.0/library` for all known `response_groups` and other parameter
   for the library endpoint.

Reuse authentication data
=========================

You can store your authentication data after an device registration with::

   auth.to_file(FILENAME)

And load the data from file to reuse it with::

   auth = audible.Authenticator.from_file(FILENAME)
