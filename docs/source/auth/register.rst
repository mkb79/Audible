==========================
Register an Audible Device
==========================

.. raw:: html

   <div class="skill-level-container">
       <span class="skill-level-badge skill-level-intermediate">Intermediate</span>
       <span class="reading-time-badge">10 min read</span>
   </div>

This page covers device registration and deregistration. For conceptual understanding, see :doc:`../intro/understanding`.

.. tip::
   **Just want to start?** See :doc:`../intro/quickstart` for complete examples.

Device Registration
===================

What Happens During Registration
---------------------------------

When you register a device, Amazon provides:

- Access tokens for API requests
- Refresh tokens for getting new access tokens
- Device-specific signing keys
- Device information (serial, type)

This data allows your application to make authenticated API requests.

.. important::
   Every device registration appears in your Amazon account under "Content and Devices" → "Devices".

Register a New Device
---------------------

Registration happens automatically with ``from_login()``:

.. code-block:: python

   import audible

   auth = audible.Authenticator.from_login(
       username="your-email@example.com",
       password="your-password",
       locale="us",  # or "uk", "de", "fr", etc.
       with_username=False  # True for pre-Amazon accounts
   )

   # Save credentials for reuse
   auth.to_file("audible-auth.json")
   
   print("✓ Device registered successfully")

This combines authorization (login) and registration in one step.

.. seealso::
   For login callbacks (2FA, CAPTCHA), see :doc:`authorization`

Best Practices
--------------

**Register once, reuse credentials:**

.. code-block:: python

   # First time: register
   auth = audible.Authenticator.from_login(...)
   auth.to_file("audible-auth.json")
   
   # Later: reuse
   auth = audible.Authenticator.from_file("audible-auth.json")

**Don't create unnecessary registrations.** Each one appears in your device list.

Device Deregistration
=====================

Remove Current Device
---------------------

To deregister the device you're currently using:

.. code-block:: python

   import audible

   # Load credentials
   auth = audible.Authenticator.from_file("audible-auth.json")
   
   # Ensure token is valid
   auth.refresh_access_token()
   
   # Deregister this device
   auth.deregister_device()
   
   print("✓ Device deregistered")

.. important::
   After deregistering, the credentials in your auth file become invalid. You'll need to re-register to use the API again.

Remove All Devices
------------------

To deregister **ALL** Audible devices (including official apps):

.. code-block:: python

   auth.deregister_device(deregister_all=True)

.. warning::
   This deregisters **every** Audible device on your account, including:
   
   - Your Python applications
   - Audible mobile apps
   - Echo devices
   - All other registered devices

   Use this only when you want to completely clear your device list.

When to Use Deregister All
---------------------------

Useful for:

- Removing "hanging" registrations from failed scripts
- Cleaning up your device list
- Starting fresh with device registrations

**To remove a single registration:**
   Open your `Amazon device list <https://www.amazon.com/hz/mycd/digital-console/contentlist/booksAll/dateDsc/>`_ and manually remove individual devices.

Requirements for Deregistration
================================

Deregistration requires a **valid access token**.

If Your Token is Expired
-------------------------

.. code-block:: python

   import audible

   auth = audible.Authenticator.from_file("audible-auth.json")
   
   # Refresh token first
   if auth.access_token_expired:
       auth.refresh_access_token()
   
   # Now deregister
   auth.deregister_device()

If You Don't Have a Refresh Token
----------------------------------

Without a refresh token, you can't programmatically deregister. Options:

1. **Manual removal:** Use Amazon's website to remove devices
2. **Re-register:** Login again, then deregister properly

Managing Device List
====================

View Your Devices
-----------------

Visit `Amazon Manage Your Content and Devices <https://www.amazon.com/hz/mycd/digital-console/devicelist>`_ to see all registered devices.

Each Python registration appears with:
- Device name (usually "Audible for iPhone")
- Registration date
- Last used date

Identify Your Registrations
----------------------------

Your Python applications appear similar to mobile apps. To identify them:

1. Note the registration timestamp
2. Match it with when you ran ``from_login()``
3. Use the device serial (stored in auth file)

Clean Up Regularly
------------------

Good practice:

- Deregister devices before deleting auth files
- Periodically review your device list
- Remove unused or abandoned registrations

Examples
========

Complete Registration Flow
--------------------------

.. code-block:: python

   import audible

   # Register new device
   auth = audible.Authenticator.from_login(
       username="user@example.com",
       password="password123",
       locale="us"
   )
   
   # Save credentials
   auth.to_file("audible-auth.json", encryption=False)
   
   # Use the API
   with audible.Client(auth=auth) as client:
       library = client.get("1.0/library", num_results=50)
       print(f"Found {library['total_results']} books")
   
   # Deregister when done (optional)
   auth.deregister_device()
   print("Device deregistered")

Reuse Existing Registration
----------------------------

.. code-block:: python

   import audible

   # Load existing credentials (no re-registration)
   auth = audible.Authenticator.from_file("audible-auth.json")
   
   # Use immediately
   with audible.Client(auth=auth) as client:
       library = client.get("1.0/library", num_results=999)

Handle Expired Tokens
----------------------

.. code-block:: python

   import audible

   auth = audible.Authenticator.from_file("audible-auth.json")
   
   # Token might be expired
   if auth.access_token_expired:
       print("Refreshing expired token...")
       auth.refresh_access_token()
       auth.to_file()  # Save new token
   
   # Continue normally
   with audible.Client(auth=auth) as client:
       library = client.get("1.0/library")

Troubleshooting
===============

"Device registration failed"
----------------------------

**Possible causes:**

1. **Wrong credentials:** Double-check username and password
2. **2FA enabled:** Use ``otp_callback`` parameter
3. **CAPTCHA required:** Use ``captcha_callback`` parameter
4. **Pre-Amazon account:** Set ``with_username=True``

See :doc:`authorization` for callback examples.

"No refresh token" Error During Deregister
-------------------------------------------

If you can't deregister programmatically:

1. **Manual removal:** Remove from Amazon's device list website
2. **Fresh registration:** Register again, then deregister properly

Can't Find Device in Amazon List
---------------------------------

Your device might appear as:

- "Audible for iPhone"
- "Audible for Android" 
- Similar mobile device names

Look for the registration timestamp to identify your Python app.

See Also
========

- :doc:`../intro/understanding` - Device registration concepts
- :doc:`authorization` - Login with callbacks
- :doc:`authentication` - Token management
- :doc:`../intro/quickstart` - Complete examples
- :doc:`../core/load_save` - Save/load credentials
