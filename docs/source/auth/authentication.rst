==============
Authentication
==============

This page covers the technical details of API authentication methods. For conceptual understanding, see :doc:`../intro/understanding`.

.. tip::
   **Just want working code?** See :doc:`../intro/quickstart`

API Authentication Methods
===========================

Audible uses two methods to authenticate API requests. The library automatically chooses the best available method.

.. code-block:: python

   # Authentication is automatic
   auth = audible.Authenticator.from_file("auth.txt")
   client = audible.Client(auth=auth)
   
   # The Authenticator handles everything

The library tries request signing first, then falls back to bearer tokens if signing credentials aren't available.

Request Signing Method
======================

Overview
--------

Request signing provides unrestricted access to the Audible API. Each request is cryptographically signed using your device's RSA private key.

**Advantages:**

- Full API access (all endpoints work)
- Most secure authentication method
- Used by official Audible iOS/Android apps

**Requirements:**

- ``adp_token`` from device registration
- ``device_private_key`` from device registration

These are obtained automatically when you use :meth:`audible.Authenticator.from_login`.

How It Works
------------

Every request includes three signed headers:

.. code-block:: text

   x-adp-token: {enc:...}
   x-adp-alg: SHA256withRSA:1.0
   x-adp-signature: <signature>:<timestamp>

The signature is computed as:

1. Concatenate: method + path + timestamp + body + adp_token
2. Sign with SHA256-RSA using private key
3. Base64 encode the signature

Amazon verifies the signature matches your registered device.

Example Headers
---------------

.. code-block:: text

   x-adp-token: {enc:AES128...}
   x-adp-alg: SHA256withRSA:1.0
   x-adp-signature: AAAAAAAA...:2019-02-16T00:00:01.000000000Z

Bearer Token Method
===================

Overview
--------

Bearer tokens are simpler but more limited. The access token is included in the Authorization header.

**Limitations:**

- Some endpoints don't work (e.g., license requests)
- Tokens expire after 60 minutes
- Must refresh regularly

**Requirements:**

- ``access_token`` from device registration or refresh

**Headers:**

.. code-block:: text

   Authorization: Bearer Atna|...
   client-id: 0

When to Use
-----------

The bearer method is used automatically when:

- Device registration credentials aren't available
- Request signing fails

You typically don't need to choose manually - the library handles it.

Access Token Lifecycle
======================

Understanding Tokens
--------------------

**Access Token:**
   - Valid for 60 minutes
   - Used for API authentication
   - Automatically refreshed by the library

**Refresh Token:**
   - Long-lived (months/years)
   - Used to get new access tokens
   - Obtained during device registration

Checking Token Status
---------------------

.. code-block:: python

   # Check if token is expired
   if auth.access_token_expired:
       print("Token has expired")
   
   # Check time remaining
   print(f"Time remaining: {auth.access_token_expires}")

Manual Token Refresh
--------------------

The library refreshes automatically, but you can force it:

.. code-block:: python

   # Force refresh
   auth.refresh_access_token(force=True)
   
   # Save updated credentials
   auth.to_file()

.. note::
   Refresh tokens are precious! If you lose your refresh token, you'll need to log in and register again.

Token Refresh Example
---------------------

.. code-block:: python

   import audible
   
   # Load saved credentials
   auth = audible.Authenticator.from_file("auth.txt")
   
   # Check token status
   if auth.access_token_expired:
       print("Access token expired, refreshing...")
       auth.refresh_access_token()
       auth.to_file()  # Save new token
   
   # Use the client normally
   with audible.Client(auth=auth) as client:
       library = client.get("1.0/library", num_results=50)

Website Authentication
======================

For web-based operations (not API calls), you need website cookies.

Using Website Cookies
---------------------

.. code-block:: python

   import audible
   import httpx
   
   auth = audible.Authenticator.from_file("auth.txt")
   
   # Use cookies with httpx
   with httpx.Client(cookies=auth.website_cookies) as client:
       resp = client.get("https://www.amazon.com/cpe/yourpayments/wallet")
       resp = client.get("https://www.audible.com")

Cookie Scope Limitations
-------------------------

Website cookies are limited to their top-level domain:

- Cookies for ``.amazon.com`` don't work on ``.amazon.de``
- Cookies for ``.audible.com`` don't work on ``.audible.de``

Setting Cookies for Different Countries
----------------------------------------

.. code-block:: python

   # Get cookies for Germany
   auth.set_website_cookies_for_country("de")
   auth.to_file()  # Save new cookies
   
   # Now cookies work for amazon.de and audible.de

.. warning::
   Setting cookies for a new country **overwrites** existing cookies. Save your auth file after changing countries.

Using Postman for Testing
==========================

Postman is useful for testing API endpoints.

Bearer Method (Easy)
--------------------

Bearer authentication works out of the box:

1. Get your access token from auth file
2. Add header in Postman: ``Authorization: Bearer <your-token>``
3. Add header: ``client-id: 0``

Request Signing (Advanced)
---------------------------

To use request signing in Postman:

1. Install `postman_util_lib <https://joolfe.github.io/postman-util-lib/>`_
2. Download :download:`pre-request-script <../../../utils/postman/pm_pre_request.js>`
3. Add the script to your Collection's "Pre-request Scripts"
4. Create environment variables:
   - ``adp-token`` - From your auth file
   - ``private-key`` - From your auth file

The script will automatically sign each request.

Authentication Flow (Automatic)
===============================

Here's what happens when you make a request:

1. **Client prepares the request**
   - Constructs URL
   - Adds query parameters

2. **Authenticator adds authentication**
   - Chooses signing or bearer method
   - Adds appropriate headers
   - Refreshes token if needed

3. **Request is sent**

4. **Response processing**
   - Checks HTTP status
   - Parses JSON
   - Returns data or raises exception

You don't need to manage any of this manually.

Troubleshooting
===============

"No refresh token" Error
-------------------------

If you see ``NoRefreshToken`` error:

1. Your auth file is incomplete
2. Re-run the login process:

.. code-block:: python

   auth = audible.Authenticator.from_login(
       username="...",
       password="...",
       locale="us"
   )
   auth.to_file("auth.txt")

401/403 Unauthorized Errors
----------------------------

If you get ``Unauthorized`` errors:

1. **Access token expired:**
   - Usually auto-refreshed
   - Try: ``auth.refresh_access_token()``

2. **Invalid credentials:**
   - Re-authenticate with ``from_login()``

3. **Rate limited:**
   - Add delays between requests
   - Wait before retrying

429 Rate Limit Errors
---------------------

If you get ``RatelimitError``:

.. code-block:: python

   import time
   
   for item in large_list:
       try:
           result = client.get(f"1.0/catalog/products/{item}")
       except audible.RatelimitError:
           print("Rate limited, waiting...")
           time.sleep(60)  # Wait 1 minute
           result = client.get(f"1.0/catalog/products/{item}")

Best Practices
==============

1. **Save credentials securely**

   .. code-block:: python

      # Use encryption
      auth.to_file("auth.txt", password="strong-password", encryption="json")

2. **Reuse authentication data**

   Don't re-register on every run. Load saved credentials:

   .. code-block:: python

      auth = audible.Authenticator.from_file("auth.txt")

3. **Handle token refresh gracefully**

   The library does this automatically, but save after manual refresh:

   .. code-block:: python

      auth.refresh_access_token()
      auth.to_file()  # Save new token

4. **Use context managers**

   Ensures proper cleanup:

   .. code-block:: python

      with audible.Client(auth=auth) as client:
          # Your code here
          pass

See Also
========

- :doc:`../intro/understanding` - Conceptual overview
- :doc:`authorization` - Login and callbacks
- :doc:`register` - Device registration
- :doc:`../misc/load_save` - Save/load credentials
- :doc:`../intro/quickstart` - Working examples
