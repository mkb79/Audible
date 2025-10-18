==========
Quickstart
==========

Get up and running with Audible in 5 minutes! This guide will take you from installation to seeing your audiobook library.

.. note::
   **What you'll learn:**
   
   - Install the library (30 seconds)
   - Authenticate with your Audible account (2 minutes)
   - Fetch your audiobook library (2 minutes)
   - What to do next (30 seconds)

Installation
============

Install Audible using pip:

.. code-block:: bash

   pip install audible

That's it! The library is now installed with all dependencies.

.. tip::
   **Python 3.10 or higher required.** Check with ``python --version``

Your First Authentication
==========================

Let's get you authenticated and save your credentials for future use.

Basic Authentication
--------------------

.. code-block:: python

   import audible

   # Login with your Amazon/Audible credentials
   auth = audible.Authenticator.from_login(
       username="your-email@example.com",
       password="your-password",
       locale="us"  # or "uk", "de", "fr", "ca", "au", etc.
   )

   # Save credentials for reuse
   auth.to_file("audible_auth.txt")
   
   print("✓ Successfully authenticated!")

.. important::
   **Keep your auth file secure!** It contains your credentials.
   Add ``audible_auth.txt`` to your ``.gitignore`` if using version control.

Common Authentication Scenarios
--------------------------------

**If you have 2-Factor Authentication (2FA):**

.. code-block:: python

   def my_otp_callback():
       return input("Enter your OTP code: ")

   auth = audible.Authenticator.from_login(
       username="your-email@example.com",
       password="your-password",
       locale="us",
       otp_callback=my_otp_callback  # Handle 2FA
   )

**If you encounter a CAPTCHA:**

.. code-block:: python

   def my_captcha_callback(captcha_url):
       print(f"Please solve CAPTCHA at: {captcha_url}")
       return input("Enter CAPTCHA answer: ")

   auth = audible.Authenticator.from_login(
       username="your-email@example.com",
       password="your-password",
       locale="us",
       captcha_callback=my_captcha_callback  # Handle CAPTCHA
   )

**Pre-Amazon Audible accounts** (US, UK, DE only):

.. code-block:: python

   auth = audible.Authenticator.from_login(
       username="your-audible-username",  # Not email!
       password="your-password",
       locale="us",
       with_username=True  # Important for pre-Amazon accounts
   )

Get Your Audiobook Library
===========================

Now let's fetch your audiobooks! This is the moment you've been waiting for.

Complete Example
----------------

.. code-block:: python
   :linenos:
   :emphasize-lines: 4-9

   import audible

   # Load your saved authentication
   auth = audible.Authenticator.from_file("audible_auth.txt")

   # Create a client and fetch your library
   with audible.Client(auth=auth) as client:
       library = client.get(
           "1.0/library",
           num_results=999,
           response_groups="product_desc, product_attrs",
           sort_by="-PurchaseDate"  # Most recent first
       )
       
       # Display your books
       print(f"\n📚 Found {library['total_results']} audiobooks!\n")
       
       for i, book in enumerate(library["items"][:10], 1):
           title = book.get("title", "Unknown")
           authors = ", ".join([a["name"] for a in book.get("authors", [])])
           
           print(f"{i}. {title}")
           print(f"   by {authors}")
           print(f"   ASIN: {book.get('asin')}\n")

**Expected Output:**

.. code-block:: text

   📚 Found 247 audiobooks!

   1. Project Hail Mary
      by Andy Weir
      ASIN: B08G9PRS1K

   2. The Midnight Library
      by Matt Haig
      ASIN: B086WP794Z

   3. Atomic Habits
      by James Clear
      ASIN: B07RFSSYBH
   
   ...

.. tip::
   **Your first successful request!** 🎉 You're now officially using the Audible API.

Understanding the Code
----------------------

Let's break down what just happened:

**Line 4:** Load your saved credentials (from the authentication step)

**Lines 7-13:** Create a client and make an API request

- ``1.0/library`` - The endpoint for your library
- ``num_results=999`` - Get up to 999 books (adjust as needed)
- ``response_groups`` - What information to include (title, authors, etc.)
- ``sort_by="-PurchaseDate"`` - Sort by purchase date (newest first)

**Lines 16-23:** Loop through results and print book information

More Examples
=============

Filter by Title
---------------

.. code-block:: python

   with audible.Client(auth=auth) as client:
       library = client.get(
           "1.0/library",
           title="Harry Potter",  # Search by title
           num_results=50
       )

Search by Author
----------------

.. code-block:: python

   with audible.Client(auth=auth) as client:
       library = client.get(
           "1.0/library",
           author="Stephen King",  # Search by author
           num_results=50
       )

Get Detailed Information
------------------------

.. code-block:: python

   with audible.Client(auth=auth) as client:
       library = client.get(
           "1.0/library",
           num_results=10,
           response_groups=(
               "product_desc, product_attrs, contributors, "
               "series, rating, reviews, media"
           )
       )
       
       for book in library["items"]:
           print(f"Title: {book['title']}")
           print(f"Runtime: {book.get('runtime_length_min', 0)} minutes")
           print(f"Rating: {book.get('rating', 'N/A')}")
           print(f"Release Date: {book.get('release_date', 'N/A')}")
           print("-" * 40)

Switch Marketplaces
-------------------

Access your books from different Audible marketplaces:

.. code-block:: python

   with audible.Client(auth=auth) as client:
       # Switch to UK marketplace
       client.switch_marketplace("uk")
       uk_library = client.get("1.0/library", num_results=50)
       
       # Switch to DE marketplace
       client.switch_marketplace("de")
       de_library = client.get("1.0/library", num_results=50)
       
       print(f"UK books: {uk_library['total_results']}")
       print(f"DE books: {de_library['total_results']}")

Troubleshooting
===============

Authentication Issues
---------------------

**"Invalid credentials" error:**

1. Double-check your email and password
2. Try logging in on the Audible website first
3. Check if 2FA is enabled (use ``otp_callback``)
4. For pre-Amazon accounts, set ``with_username=True``

**Stuck in CAPTCHA loop:**

This happens when Amazon flags your IP as suspicious.

**Solutions:**

- Wait 15-30 minutes before trying again
- Use ``from_login_external()`` for browser-based login
- Try from a different network

**"Too many requests" error:**

You're making requests too quickly. Add a small delay:

.. code-block:: python

   import time
   
   # Between requests
   time.sleep(1)  # Wait 1 second

Can't Find Books
----------------

**No results returned:**

- Check if ``num_results`` is too low
- Verify you're using the correct marketplace
- Ensure your search filters aren't too restrictive

**Missing book information:**

Add more ``response_groups`` to get detailed information:

.. code-block:: python

   response_groups="product_desc, product_attrs, contributors, series"

Next Steps
==========

Congratulations! You've successfully:

✓ Installed the Audible library

✓ Authenticated with your account

✓ Fetched your audiobook library

✓ Learned basic filtering and searching

Where to Go from Here
---------------------

**Learn More:**

- :doc:`understanding` - Detailed concepts and architecture
- :doc:`../auth/authorization` - Advanced authentication options
- :doc:`../misc/advanced` - Advanced features and patterns
- :doc:`../misc/examples` - More code examples

**API Documentation:**

- :doc:`../modules/audible` - Complete API reference
- :doc:`../misc/external_api` - Audible API endpoints

**Need Help?**

- :doc:`../misc/logging` - Enable debug logging
- `GitHub Issues <https://github.com/mkb79/audible/issues>`_ - Report bugs
- `GitHub Discussions <https://github.com/mkb79/audible/discussions>`_ - Ask questions

Common Next Tasks
-----------------

**Export your library to CSV:**

.. code-block:: python

   import csv
   
   with audible.Client(auth=auth) as client:
       library = client.get("1.0/library", num_results=999)
       
       with open("my_audiobooks.csv", "w", newline="", encoding="utf-8") as f:
           writer = csv.writer(f)
           writer.writerow(["Title", "Author", "ASIN", "Purchase Date"])
           
           for book in library["items"]:
               title = book.get("title", "")
               authors = ", ".join([a["name"] for a in book.get("authors", [])])
               asin = book.get("asin", "")
               purchase_date = book.get("purchase_date", "")
               
               writer.writerow([title, authors, asin, purchase_date])

**Get activation bytes** (for DRM removal):

.. code-block:: python

   auth = audible.Authenticator.from_file("audible_auth.txt")
   activation_bytes = auth.get_activation_bytes()
   print(f"Your activation bytes: {activation_bytes}")

.. attention::
   Only use activation bytes for your own audiobooks for personal archiving.

**Use async/await** (for faster requests):

.. code-block:: python

   import asyncio
   import audible

   async def get_library():
       auth = audible.Authenticator.from_file("audible_auth.txt")
       
       async with audible.AsyncClient(auth=auth) as client:
           library = await client.get("1.0/library", num_results=999)
           return library

   # Run the async function
   library = asyncio.run(get_library())

Related Projects
================

- `audible-cli <https://github.com/mkb79/audible-cli>`_ - Command-line interface for downloading audiobooks

Happy listening! 🎧
