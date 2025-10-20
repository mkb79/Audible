===========================
Frequently Asked Questions
===========================

.. raw:: html

   <div class="skill-level-container">
       <span class="skill-level-badge skill-level-all">All Levels</span>
       <span class="reading-time-badge">12 min read</span>
   </div>

Find answers to common questions about the Audible library. Can't find what you're looking for? Check :doc:`troubleshooting` or visit our `GitHub Discussions <https://github.com/mkb79/audible/discussions>`_.

.. contents:: Quick Navigation
   :local:
   :depth: 2

Installation & Setup
====================

How do I install the library?
------------------------------

**Basic installation:**

.. code-block:: bash

   pip install audible

**With specific Python version:**

.. code-block:: bash

   python3.11 -m pip install audible

**Upgrade to latest version:**

.. code-block:: bash

   pip install --upgrade audible

What Python versions are supported?
------------------------------------

Python 3.10 or higher is required. Check your version:

.. code-block:: bash

   python --version

Can I use this library with audible-cli?
-----------------------------------------

Yes! `audible-cli <https://github.com/mkb79/audible-cli>`_ is built on top of this library. You can use both together and share authentication files.

Authentication
==============

Why does authentication fail with "Invalid credentials"?
---------------------------------------------------------

**Common causes:**

1. **Incorrect email/password** - Double-check your credentials
2. **2FA enabled** - Use ``otp_callback`` parameter (see :doc:`../auth/authentication`)
3. **Pre-Amazon account** - Set ``with_username=True``
4. **Amazon security block** - Your IP might be flagged

**Solution for 2FA:**

.. code-block:: python

   def my_otp_callback():
       return input("Enter OTP: ")

   auth = audible.Authenticator.from_login(
       username="email@example.com",
       password="password",
       locale="us",
       otp_callback=my_otp_callback
   )

How do I authenticate without entering credentials in code?
------------------------------------------------------------

Use external browser authentication:

.. code-block:: python

   import audible

   auth = audible.Authenticator.from_login_external(locale="us")
   auth.to_file("audible-auth.json")

This opens your browser where you can log in securely. See :doc:`../auth/authorization` for details.

How long does authentication last?
-----------------------------------

- **Access tokens** expire after ~60 minutes
- **Refresh tokens** last ~1 year
- **Device registration** persists until deregistered

The library automatically refreshes access tokens when needed.

Can I use multiple Audible accounts?
-------------------------------------

Yes! Save each account's credentials separately:

.. code-block:: python

   # Account 1
   auth1 = audible.Authenticator.from_login(...)
   auth1.to_file("audible-auth-account1.json")

   # Account 2
   auth2 = audible.Authenticator.from_login(...)
   auth2.to_file("audible-auth-account2.json")

   # Use them
   client1 = audible.Client(auth=auth1)
   client2 = audible.Client(auth=auth2)

See :ref:`advanced/client_api:Switch User` for switching between accounts.

Where should I store my auth file?
-----------------------------------

**Best practices:**

.. code-block:: python

   from pathlib import Path

   # User's home directory
   auth_file = Path.home() / ".audible" / "audible-auth.json"
   auth_file.parent.mkdir(exist_ok=True)

   auth.to_file(str(auth_file))

**Security tips:**

- Never commit auth files to version control
- Add to ``.gitignore``: ``audible-auth*.json``, ``audible-auth*.bin``
- Set restrictive file permissions on Unix: ``chmod 600 audible-auth.json``

API Requests
============

Why do I get "Too many requests" errors?
-----------------------------------------

Amazon rate-limits API requests. Add delays between requests:

.. code-block:: python

   import time

   with audible.Client(auth=auth) as client:
       for marketplace in ["us", "uk", "de"]:
           client.switch_marketplace(marketplace)
           library = client.get("1.0/library", num_results=50)
           time.sleep(1)  # Wait 1 second between requests

What API endpoints are available?
----------------------------------

See :doc:`external_api` for a complete list. Common endpoints:

- ``1.0/library`` - Your audiobook library
- ``1.0/library/{asin}`` - Specific book details
- ``1.0/wishlist`` - Your wishlist
- ``1.0/stats/aggregates`` - Listening statistics
- ``1.0/catalog/products/{asin}`` - Catalog information

How do I get more book details?
--------------------------------

Use the ``response_groups`` parameter:

.. code-block:: python

   library = client.get(
       "1.0/library",
       num_results=50,
       response_groups=(
           "product_desc, product_attrs, media, contributors, "
           "customer_rights, series, reviews, rating"
       )
   )

Available response groups vary by endpoint. See :doc:`external_api`.

Can I download audiobook files?
--------------------------------

This library provides API access only. For downloading audiobooks, use `audible-cli <https://github.com/mkb79/audible-cli>`_:

.. code-block:: bash

   # Install audible-cli
   pip install audible-cli

   # Download a book
   audible download -a B002V5D7PC

Why are some books missing from my library?
--------------------------------------------

**Common reasons:**

1. **num_results too low** - Default is 50, you might have more books
2. **Wrong marketplace** - Books are marketplace-specific
3. **Filters applied** - Check your query parameters

**Get all books:**

.. code-block:: python

   library = client.get("1.0/library", num_results=1000)
   print(f"Total books: {library['total_results']}")

Marketplaces
============

Which marketplaces are supported?
----------------------------------

All Audible marketplaces:

- **us** - United States (audible.com)
- **uk** - United Kingdom (audible.co.uk)
- **de** - Germany (audible.de)
- **fr** - France (audible.fr)
- **ca** - Canada (audible.ca)
- **au** - Australia (audible.com.au)
- **jp** - Japan (audible.co.jp)
- **it** - Italy (audible.it)
- **in** - India (audible.in)
- **es** - Spain (audible.es)

See :doc:`../marketplaces/marketplaces` for more details.

How do I switch between marketplaces?
--------------------------------------

.. code-block:: python

   with audible.Client(auth=auth) as client:
       # Current marketplace
       print(client.marketplace)  # "us"

       # Switch to UK
       client.switch_marketplace("uk")
       uk_library = client.get("1.0/library")

       # Switch to Germany
       client.switch_marketplace("de")
       de_library = client.get("1.0/library")

Do I need separate accounts for each marketplace?
--------------------------------------------------

No! One Amazon account can access multiple marketplaces. However, your library is different in each marketplace.

Async/Await
===========

When should I use AsyncClient instead of Client?
-------------------------------------------------

Use ``AsyncClient`` when:

- Making many concurrent requests
- Your application is already async
- You need better performance for bulk operations

**Performance comparison:**

.. code-block:: python

   # Sync - processes one at a time (~5 seconds)
   for asin in asins:
       book = client.get(f"1.0/library/{asin}")

   # Async - processes concurrently (~1 second)
   async with audible.AsyncClient(auth=auth) as client:
       tasks = [client.get(f"1.0/library/{asin}") for asin in asins]
       books = await asyncio.gather(*tasks)

See :doc:`../core/async` for complete examples.

How do I convert my sync code to async?
----------------------------------------

**Sync version:**

.. code-block:: python

   import audible

   auth = audible.Authenticator.from_file("audible-auth.json")
   with audible.Client(auth=auth) as client:
       library = client.get("1.0/library")

**Async version:**

.. code-block:: python

   import asyncio
   import audible

   async def main():
       auth = audible.Authenticator.from_file("audible-auth.json")
       async with audible.AsyncClient(auth=auth) as client:
           library = await client.get("1.0/library")
       return library

   # Run it
   library = asyncio.run(main())

Advanced Topics
===============

How do I get activation bytes?
-------------------------------

.. code-block:: python

   auth = audible.Authenticator.from_file("audible-auth.json")
   activation_bytes = auth.get_activation_bytes()
   print(f"Activation bytes: {activation_bytes}")

.. attention::
   Only use activation bytes for your own audiobooks for personal archiving purposes.

Can I use custom httpx client settings?
----------------------------------------

Yes! Pass httpx parameters to the Client:

.. code-block:: python

   import httpx

   # Custom timeout
   client = audible.Client(
       auth=auth,
       timeout=30.0
   )

   # Custom headers
   client = audible.Client(
       auth=auth,
       headers={"User-Agent": "MyApp/1.0"}
   )

   # Proxy support
   client = audible.Client(
       auth=auth,
       proxies="http://proxy.example.com:8080"
   )

See :doc:`../advanced/client_api` for more options.

How do I enable debug logging?
-------------------------------

.. code-block:: python

   import logging

   # Enable debug logging
   logging.basicConfig(
       level=logging.DEBUG,
       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
   )

See :doc:`../advanced/logging` for detailed logging configuration.

How do I save/load authentication with encryption?
---------------------------------------------------

.. code-block:: python

   # Save with password encryption
   auth.to_file("audible-auth.json", password="my-secret-password", encryption="json")

   # Load encrypted file
   auth = audible.Authenticator.from_file(
       "audible-auth.json",
       password="my-secret-password"
   )

See :doc:`../core/load_save` for more details.

Troubleshooting
===============

The library suddenly stopped working. What happened?
-----------------------------------------------------

**Common causes:**

1. **Access token expired** - Refresh it:

   .. code-block:: python

      auth.refresh_access_token()

2. **API changes** - Update the library:

   .. code-block:: bash

      pip install --upgrade audible

3. **Device deregistered** - Re-authenticate

See :doc:`troubleshooting` for more solutions.

How do I report a bug?
----------------------

1. Check existing `GitHub Issues <https://github.com/mkb79/audible/issues>`_
2. Create a new issue with:

   - Python version (``python --version``)
   - Library version (``pip show audible``)
   - Minimal code to reproduce
   - Full error traceback
   - Expected vs actual behavior

Can I use this for commercial purposes?
----------------------------------------

The library is MIT licensed, allowing commercial use. However:

- Respect Amazon's Terms of Service
- Don't abuse the API with excessive requests
- Don't redistribute audiobook content
- Use only for personal or legitimate business purposes

Contributing
============

How can I contribute to the project?
-------------------------------------

Contributions are welcome! You can:

- Report bugs via GitHub Issues
- Suggest features in GitHub Discussions
- Submit pull requests
- Improve documentation
- Share examples and use cases

See the `Contributing Guide <https://github.com/mkb79/audible/blob/master/CONTRIBUTING.md>`_ for details.

Still Have Questions?
=====================

- **Browse Examples:** :doc:`examples`
- **Check Troubleshooting:** :doc:`troubleshooting`
- **Read API Docs:** :doc:`../modules/audible`
- **Ask the Community:** `GitHub Discussions <https://github.com/mkb79/audible/discussions>`_
- **Report Issues:** `GitHub Issues <https://github.com/mkb79/audible/issues>`_
