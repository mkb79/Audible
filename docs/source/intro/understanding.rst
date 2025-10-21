=====================
Understanding Audible
=====================

.. raw:: html

   <div class="skill-level-container">
       <span class="skill-level-badge skill-level-beginner">Beginner</span>
       <span class="reading-time-badge">10 min read</span>
   </div>

This guide explains the core concepts behind the Audible library and how it interacts with Amazon's authentication system.

.. tip::
   **Want to start coding immediately?** Jump to :doc:`quickstart`

   **Need technical details?** See :doc:`../auth/authentication` and :doc:`../auth/authorization`

.. note::
   **What you'll learn:**

   - How Audible authentication works
   - What device registration means
   - The authentication architecture
   - Key concepts and terminology

Overview
========

The Audible library provides a Python interface to Amazon's non-public Audible API. Unlike public APIs, Audible requires device-based authentication that mimics how official Audible apps communicate with Amazon's servers.

Authentication Architecture
===========================

The Two-Step Process
--------------------

Authentication with Audible happens in two distinct stages:

**Stage 1: Authorization (Login)**
   You prove your identity to Amazon using your credentials. Amazon returns an authorization code.

**Stage 2: Device Registration**
   Your application registers as a virtual "Audible device" using the authorization code. Amazon returns long-term credentials.

This two-step process is similar to how real Audible apps work:

1. You log in once with your Amazon account
2. Your device is registered as trusted
3. Future access uses stored credentials without repeated logins

Why This Approach?
------------------

**Security:** OAuth 2.0 with PKCE (Proof Key for Code Exchange) protects against authorization code interception.

**Convenience:** Once registered, your application can make API requests without password prompts.

**Device Model:** Amazon treats each registered application like a physical device (phone, tablet, etc.).

OAuth 2.0 with PKCE
-------------------

Audible uses OAuth 2.0 with PKCE, a security standard designed for native applications:

**The Flow:**

1. Generate a random ``code_verifier`` (a secret)
2. Create a ``code_challenge`` (SHA256 hash of the verifier)
3. Send the challenge during login
4. Send the verifier during device registration
5. Amazon verifies they match

This prevents attackers who intercept the authorization code from using it without the original verifier.

.. seealso::
   For implementation details and code examples, see :doc:`../auth/authorization`

Device Registration Concept
============================

What is a "Device"?
-------------------

In Amazon's ecosystem, a "device" is any application authorized to access your Audible content:

- Audible iOS/Android apps
- Echo devices
- **Your Python application**

Each device gets unique credentials that identify it to Amazon.

What You Receive
----------------

After registration, Amazon provides:

**Authentication Credentials:**
   - Short-lived access tokens (60 minutes)
   - Long-lived refresh tokens
   - Device-specific signing keys

**Device Information:**
   - Unique device serial number
   - Device type identification
   - Registration timestamp

These credentials enable authenticated API requests without password re-entry.

.. seealso::
   For registration code and deregistration, see :doc:`../auth/register`

Authentication Methods
======================

The library supports two authentication methods:

1. Request Signing (Preferred)
-------------------------------

**Concept:** Every API request is cryptographically signed using your device's private key.

**Advantages:**
   - Unrestricted API access
   - Most secure method
   - No token expiration concerns

**When Available:**
   Automatically when you have device registration credentials.

2. Bearer Token (Fallback)
---------------------------

**Concept:** Include an access token in request headers.

**Limitations:**
   - Some endpoints don't work
   - Tokens expire every 60 minutes
   - Requires regular refresh

**When Used:**
   Fallback when device registration isn't available.

The library automatically chooses the best method available.

.. seealso::
   For technical details, headers, and examples, see :doc:`../auth/authentication`

Marketplaces
============

Audible operates separate marketplaces for different regions, each with its own content catalog and pricing.

Key Concepts
------------

**Library Separation:**
   Books purchased on Audible.com don't appear in Audible.de (even with the same account).

**Credential Portability:**
   Your authentication credentials work across all marketplaces - you can switch between them.

**Website Cookies:**
   Have domain-specific scope (e.g., .amazon.com vs .amazon.de).

.. seealso::
   For complete marketplace list and country codes, see :doc:`../marketplaces/marketplaces`

API Structure
=============

Endpoints
---------

Audible API uses versioned endpoints:

- **v1.0** - Current version (default)
- **v0.0** - Legacy (deprecated)

Example:
   ``https://api.audible.com/1.0/library``

Response Groups
---------------

Control response detail level:

**Minimal:**
   Basic information only

**Standard:**
   Common attributes

**Detailed:**
   Comprehensive data

**Important:** More data = slower responses. Request only what you need.

.. seealso::
   For complete API reference, see :doc:`../help/external_api`

Security Considerations
=======================

Protecting Credentials
----------------------

Your authentication file contains sensitive data. Best practices:

1. **Never commit to version control** - Add to ``.gitignore``
2. **Use file encryption** - Protect stored credentials
3. **Restrict file permissions** - ``chmod 600`` on Unix systems
4. **Don't share auth files** - Each user creates their own

Rate Limiting
-------------

Amazon monitors API usage. To avoid issues:

- Add delays between bulk requests (1-2 seconds)
- Don't make thousands of requests rapidly
- Cache data when possible

Pre-Amazon Accounts
-------------------

Audible originally had separate logins before Amazon integration.

**If you have a pre-Amazon account:**
   - Login with Audible username (not email)
   - Only for US, UK, DE marketplaces
   - Use ``with_username=True``

**Modern Amazon accounts:**
   - Login with Amazon email
   - All marketplaces
   - Default behavior

Sync vs Async
=============

The library provides both interfaces:

**Synchronous (``Client``):**
   - Traditional blocking I/O
   - Simpler to use
   - One request at a time

**Asynchronous (``AsyncClient``):**
   - Non-blocking I/O
   - Better performance for bulk operations
   - Requires ``async``/``await``

Both share the same authentication system.

.. seealso::
   For async examples, see :doc:`../core/async`

Next Steps
==========

Now that you understand the concepts:

**Get Started:**
   - :doc:`quickstart` - Working code in 5 minutes
   - :doc:`../auth/authorization` - Login and callbacks
   - :doc:`../auth/authentication` - Technical details

**Deep Dives:**
   - :doc:`../auth/register` - Device registration
   - :doc:`../core/load_save` - Save/load credentials
   - :doc:`../advanced/client_api` - Advanced patterns

**Reference:**
   - :doc:`../help/external_api` - Available endpoints
   - :doc:`../modules/audible` - Complete API docs

Common Questions
================

**Do I need a subscription?**
   You need an Audible account with books. Subscription is not required.

**Can I download audiobook files?**
   This library provides API access. Check out `audible-cli <https://github.com/mkb79/audible-cli>`_ for downloads.

**Why is my "device" listed on Amazon?**
   Device registration creates an entry. This is normal and expected.

**Is this legal?**
   Access your own content only. Respect copyright and Amazon's terms of service.
