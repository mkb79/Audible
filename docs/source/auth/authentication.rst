==============
Authentication
==============

API Authentication
==================

Audible uses the `sign request` or the `bearer` method to authenticate the
requests to the Audible API.

The authentication is done automatically when using the 
:class:`audible.Authenticator`. Simply use the ``Authenticator`` with
the :class:`audible.Client` or :class:`audible.AsyncClient` like so::

   auth = audible.Authenticator.from_file(...)
   client = audible.Client(auth=auth)

The Authenticator will try to use the sign request method if available.
Otherwise the Authenticator will try the bearer method. If no method is
available an exception is raised.

Sign request method
-------------------

With the sign request method you gain unrestricted access to the Audible API.
To use this method, you need the RSA private key and the adp_token from a
*device registration*. This method is used by the Audible apps for iOS and
Android too. A device registration is done automatically with
:meth:`audible.Authenticator.from_login` or
:meth:`audible.Authenticator.from_login_external`

Request signing is fairly straight-forward and uses a signed SHA256 digest.
Headers look like::

   x-adp-alg: SHA256withRSA:1.0
   x-adp-signature: AAAAAAAA...:2019-02-16T00:00:01.000000000Z,
   x-adp-token: {enc:...}

Bearer method
-------------

API requests with the bearer method have some restrictions. Some API call, like
the :http:post:`/1.0/content/(string:asin)/licenserequest`, doesn't work. To use
the bearer method you need an access token and a client id. You receive the
token after a device registration. Which values are valid for the client-id 
is unknown but 0 does work. An access token expires after 60 minutes. It 
can be renewed with a refresh token. A refresh token is obtained by a device 
registration only. Headers for the bearer method look like::

   Authorization: Bearer Atna|...
   client-id: 0

Website Authentication
======================

To authenticate website requests you need the website cookies received from an
authorization or device registration.

You can use the website cookies from an ``Authenticator`` with a
:class:`httpx.Client` or :class:`httpx.AsyncClient` like so::

   auth = audible.Authenticator.from_file(...)
   with httpx.Client(cookies=auth.website_cookies) as client:
       resp = client.get("https://www.amazon.com/cpe/yourpayments/wallet?ref_=ya_d_c_pmt_mpo")
       resp = client.get("https://www.audible.com")

.. note::

   Website cookies are limited to the scope of a top level domain
   (e.g. com, de, ...). To set website cookies for another top level domain
   scope, you can call ``auth.set_website_cookies_for_country(COUNTRY_CODE)``.

.. warning::

   Set website cookies for another country will override the old ones. If you
   want to keep the new cookies, please make sure to save your authentication data.

Using Postman for authentication
================================

`Postman <https://www.postman.com>`_ is a helpful utility to test API's.

To use Postman with the Audible API, every request needs to be authenticated.
You can use the bearer method (with his limitions) with Postman out of the box.

Using the sign request method with Postman is possible, but needs some extra work.

HOWTO:

1. Install the `postman_util_lib <https://joolfe.github.io/postman-util-lib/>`_
2. Copy the content from the :download:`pre-request-script <../../../utils/postman/pm_pre_request.js>` 
   into the `Pre-request Scripts` Tab for the Collection or request
3. Create an Environment and define the variables `adp-token` and `private key`
   with the counterparts from the authentication data file
