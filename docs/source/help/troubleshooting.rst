===============
Troubleshooting
===============

.. raw:: html

   <div class="skill-level-container">
       <span class="skill-level-badge skill-level-all">All Levels</span>
       <span class="reading-time-badge">15 min read</span>
   </div>

This page covers common issues and solutions when using the Audible library.

Authentication Issues
=====================

Invalid Credentials Error
-------------------------

**Problem:** You're getting "Invalid credentials" or "Login failed" errors.

.. tip::
   **Quick fixes to try first:**
   
   1. Verify your email and password are correct
   2. Try logging in on the Audible website first
   3. Check if you need 2FA/OTP authentication
   4. For pre-Amazon accounts (US/UK/DE only), set ``with_username=True``

**Solution for 2FA/OTP:**

.. code-block:: python

   def handle_otp():
       return input("Enter your OTP code: ")
   
   auth = audible.Authenticator.from_login(
       username="your-email@example.com",
       password="your-password",
       locale="us",
       otp_callback=handle_otp
   )

**Solution for pre-Amazon accounts:**

.. code-block:: python

   auth = audible.Authenticator.from_login(
       username="your-audible-username",  # Not email!
       password="your-password",
       locale="us",
       with_username=True  # Critical for pre-Amazon accounts
   )

CAPTCHA Loop
------------

**Problem:** You're stuck in an endless CAPTCHA loop or getting repeated CAPTCHA requests.

.. warning::
   This typically happens when Amazon flags your IP as suspicious due to:
   
   - Too many failed login attempts
   - Unusual geographic location
   - Using a VPN or proxy
   - Automated request patterns

**Solutions:**

1. **Wait it out** - Wait 15-30 minutes before trying again
2. **Use external browser login** - More reliable for development:

.. code-block:: python

   auth = audible.Authenticator.from_login_external(locale="us")
   # Opens browser for authentication

3. **Try different network** - Switch to mobile hotspot or different WiFi
4. **Verify on Amazon** - Log in manually on Amazon.com first

**Custom CAPTCHA handler:**

.. code-block:: python

   def handle_captcha(captcha_url):
       print(f"Solve CAPTCHA at: {captcha_url}")
       return input("Enter CAPTCHA solution: ")
   
   auth = audible.Authenticator.from_login(
       username="your-email@example.com",
       password="your-password",
       locale="us",
       captcha_callback=handle_captcha
   )

Access Token Expired
--------------------

**Problem:** Getting ``NotAuthenticatedError`` or "Access token expired" errors.

.. note::
   Access tokens expire after 60 minutes. This is normal Audible API behavior.

**Solution:** Refresh your token or re-authenticate:

.. code-block:: python

   try:
       library = client.get("1.0/library")
   except audible.exceptions.NotAuthenticatedError:
       # Option 1: Refresh the token
       auth.refresh_access_token()
       
       # Option 2: Re-authenticate completely
       auth = audible.Authenticator.from_login(
           username="your-email@example.com",
           password="your-password",
           locale="us"
       )
       
       # Try again
       library = client.get("1.0/library")

Corrupted Auth File
-------------------

**Problem:** Getting decryption errors or "corrupted auth file" messages.

.. danger::
   If your auth file is corrupted, you'll need to re-authenticate. There's no
   way to recover the file.

**Solution:**

.. code-block:: python

   import os
   
   # Delete old corrupted file
   if os.path.exists("audible-auth.json"):
       os.remove("audible-auth.json")
   
   # Create new authentication
   auth = audible.Authenticator.from_login(
       username="your-email@example.com",
       password="your-password",
       locale="us"
   )
   
   # Save to new file
   auth.to_file("audible-auth.json")

API Request Issues
==================

Rate Limit Exceeded (429 Error)
--------------------------------

**Problem:** Getting "Too many requests" or HTTP 429 errors.

.. warning::
   Audible has rate limits to prevent abuse. Making too many requests too
   quickly will trigger rate limiting.

**Solution:** Implement exponential backoff:

.. code-block:: python

   import time
   from audible.exceptions import RateLimitError
   
   def make_request_with_retry(client, endpoint, max_retries=3):
       """Make API request with automatic retry on rate limit."""
       for attempt in range(max_retries):
           try:
               return client.get(endpoint)
           except RateLimitError as e:
               if attempt < max_retries - 1:
                   wait_time = 2 ** attempt  # 1s, 2s, 4s
                   print(f"Rate limited. Waiting {wait_time}s before retry...")
                   time.sleep(wait_time)
               else:
                   print("Max retries reached. Rate limit still active.")
                   raise
   
   # Usage
   library = make_request_with_retry(client, "1.0/library")

.. tip::
   **Best practices to avoid rate limiting:**
   
   - Add 1-2 second delays between requests
   - Batch your operations when possible
   - Use ``num_results`` to get more data per request
   - Cache responses when appropriate

Empty or Missing Data
---------------------

**Problem:** API returns empty results or missing fields.

**Causes and Solutions:**

1. **Wrong marketplace selected:**

.. code-block:: python

   # Verify you're using the correct marketplace
   print(f"Current locale: {auth.locale}")
   
   # Switch if needed
   auth.switch_marketplace("uk")  # or "us", "de", "fr", etc.

2. **Insufficient response groups:**

.. code-block:: python

   # Request more detailed information
   library = client.get(
       "1.0/library",
       response_groups=(
           "product_desc, product_attrs, contributors, "
           "series, media, relationships"
       )
   )

3. **Pagination needed:**

.. code-block:: python

   # Get all items with pagination
   all_items = []
   page = 1
   
   while True:
       response = client.get(
           "1.0/library",
           num_results=50,
           page=page
       )
       
       items = response.get("items", [])
       if not items:
           break
           
       all_items.extend(items)
       page += 1
       
       # Safety check
       if page > 100:
           break

Connection Errors
-----------------

**Problem:** Network timeouts or connection errors.

.. code-block:: python

   from audible.exceptions import NetworkError
   import time
   
   def robust_request(client, endpoint, max_attempts=3):
       """Make request with connection error handling."""
       for attempt in range(max_attempts):
           try:
               return client.get(endpoint)
           except NetworkError as e:
               if attempt < max_attempts - 1:
                   print(f"Connection error. Retrying... ({attempt+1}/{max_attempts})")
                   time.sleep(2)
               else:
                   print("Connection failed after multiple attempts.")
                   raise

Installation & Dependencies
============================

Import Errors
-------------

**Problem:** ``ImportError`` or ``ModuleNotFoundError`` when importing audible.

**Solution:**

.. code-block:: bash

   # Ensure audible is installed
   pip install --upgrade audible
   
   # Verify installation
   python -c "import audible; print(audible.__version__)"

**Problem:** Conflicts with other packages.

**Solution:** Use a virtual environment:

.. code-block:: bash

   # Create virtual environment
   python -m venv venv
   
   # Activate it
   # On Windows:
   venv\\Scripts\\activate
   # On macOS/Linux:
   source venv/bin/activate
   
   # Install audible in isolated environment
   pip install audible

Python Version Issues
---------------------

**Problem:** Code doesn't work or gives syntax errors.

.. important::
   Audible requires **Python 3.10 or higher**. Check your version:

.. code-block:: bash

   python --version
   # Should show Python 3.10.x or higher

**Solution:** Upgrade Python:

- **Windows/macOS:** Download from https://www.python.org/downloads/
- **Ubuntu/Debian:** ``sudo apt install python3.11``
- **macOS (Homebrew):** ``brew install python@3.11``

Type Checking Issues
--------------------

**Problem:** mypy or type checkers complain about Audible types.

.. code-block:: bash

   # Install type stubs
   pip install types-requests
   
   # Audible includes full type hints by default
   # Ensure you're using a recent version
   pip install --upgrade audible

Async/Await Issues
==================

Event Loop Already Running
--------------------------

**Problem:** ``RuntimeError: This event loop is already running``

This commonly happens in Jupyter notebooks or when nesting async calls.

**Solution for Jupyter:**

.. code-block:: python

   # Install nest_asyncio
   pip install nest_asyncio
   
   # In your code
   import nest_asyncio
   nest_asyncio.apply()
   
   # Now async code works in Jupyter
   library = await client.get("1.0/library")

**Solution for nested async:**

.. code-block:: python

   import asyncio
   
   async def main():
       async with audible.AsyncClient(auth=auth) as client:
           library = await client.get("1.0/library")
           return library
   
   # Don't nest asyncio.run() calls
   if __name__ == "__main__":
       result = asyncio.run(main())

AsyncClient Not Closing
------------------------

**Problem:** Warning about unclosed clients or connections.

.. code-block:: python

   # Always use context manager
   async with audible.AsyncClient(auth=auth) as client:
       library = await client.get("1.0/library")
   # Client automatically closed here
   
   # Or manually close
   client = audible.AsyncClient(auth=auth)
   try:
       library = await client.get("1.0/library")
   finally:
       await client.close()

Marketplace & Localization
===========================

Wrong Marketplace
-----------------

**Problem:** Can't find your books or getting wrong language content.

.. seealso::
   See :doc:`../marketplaces/marketplaces` for full marketplace documentation.

**Solution:** Verify and switch marketplace:

.. code-block:: python

   # Check current marketplace
   print(f"Current: {auth.locale.country_code}")
   print(f"Domain: {auth.locale.domain}")
   
   # Switch to different marketplace
   auth.switch_marketplace("de")  # Germany
   # or "uk", "fr", "ca", "au", "in", "jp", "it", "es"
   
   # Fetch library from new marketplace
   with audible.Client(auth=auth) as client:
       library = client.get("1.0/library")

Multiple Marketplaces
---------------------

**Problem:** Need to access content from multiple marketplaces.

.. code-block:: python

   import audible

   # Option 1: Use same auth, switch marketplace
   auth = audible.Authenticator.from_file("audible-auth.json")

   with audible.Client(auth=auth) as client:
       # US library
       us_library = client.get("1.0/library")

       # Switch to UK
       client.switch_marketplace("uk")
       uk_library = client.get("1.0/library")

   # Option 2: Separate auth for each marketplace
   auth_us = audible.Authenticator.from_file("audible-auth-us.json")
   auth_de = audible.Authenticator.from_file("audible-auth-de.json")

   with audible.Client(auth=auth_us) as us_client:
       us_library = us_client.get("1.0/library")

   with audible.Client(auth=auth_de) as de_client:
       de_library = de_client.get("1.0/library")

Activation Bytes
================

Can't Get Activation Bytes
---------------------------

**Problem:** ``get_activation_bytes()`` fails or returns empty.

.. code-block:: python

   # Ensure you're authenticated properly
   auth = audible.Authenticator.from_file("audible-auth.json")
   
   # Method 1: Via auth object
   activation_bytes = auth.get_activation_bytes()
   
   # Method 2: Via separate function
   from audible import activation_bytes as ab
   bytes_value = ab.get_activation_bytes(auth)
   
   print(f"Activation bytes: {bytes_value}")

.. important::
   Only use activation bytes for your own audiobooks for personal backup purposes.
   Sharing or using activation bytes for piracy is illegal.

Frequently Asked Questions
===========================

General Questions
-----------------

**Q: Is using this library legal?**

A: Yes, using the library to access your own Audible account and content is legal.
However, sharing your credentials or content with others may violate Audible's
Terms of Service.

**Q: Will my account get banned?**

A: The library uses the same API that official Audible apps use. Normal usage
should not cause issues. However:

- Don't make excessive API requests (rate limiting)
- Don't share your account or content
- Use for personal purposes only

**Q: Can I download audiobooks?**

A: The library provides access to the API. For downloading audiobooks, check out
the `audible-cli <https://github.com/mkb79/audible-cli>`_ package which includes
download functionality.

**Q: Does this work with Audible Plus catalog?**

A: Yes, the library works with both purchased titles and Plus catalog content.

**Q: Can I add books to my library or wishlist?**

A: Yes! The library provides full API access including POST requests:

.. code-block:: python

   # Add to wishlist
   client.post(
       "1.0/wishlist",
       body={"asin": "B004V00AEG"}
   )

Technical Questions
-------------------

**Q: What's the difference between Client and AsyncClient?**

A: ``Client`` is synchronous (blocking), ``AsyncClient`` is asynchronous (non-blocking).
Use ``AsyncClient`` for concurrent requests or in async applications.

**Q: How long do access tokens last?**

A: Access tokens expire after 60 minutes. You can refresh them with
``auth.refresh_access_token()`` or re-authenticate.

**Q: Can I use this in a web application?**

A: Yes, but be careful with authentication. Store credentials securely and
never expose them to clients. Consider using a backend API to proxy requests.

**Q: Does this support Python 2?**

A: No. Python 2 reached end-of-life in 2020. Audible requires Python 3.10+.

**Q: Why httpx instead of requests?**

A: httpx provides both sync and async support, better HTTP/2 support, and
modern API design. This allows the library to provide both Client and AsyncClient
with a single implementation.

Still Having Issues?
====================

If your issue isn't covered here:

1. **Check the logs** - Enable debug logging: :doc:`../advanced/logging`
2. **Search GitHub Issues** - https://github.com/mkb79/audible/issues
3. **Ask on Discussions** - https://github.com/mkb79/audible/discussions
4. **File a new issue** - With full error messages and minimal reproduction code

.. tip::
   **When reporting issues, always include:**
   
   - Python version (``python --version``)
   - Audible version (``pip show audible``)
   - Full error traceback
   - Minimal code to reproduce the issue
   - Your operating system
