==============
Advanced Usage
==============

Client classes
==============

Here are some information about the ``Client`` and  the ``AsyncClient`` classes.

Both client classes have the following methods to send requests 
to the external API:

- get
- post
- delete
- patch

Make API requests
-----------------

The external Audible API offers currently two API versions, `0.0` and 
`1.0`. The Client use the `1.0` by default. So both terms are equal::

   resp = client.get("library")
   resp = client.get("1.0/library")

Each query parameter can be written as a separat keyword argument or you can
merge them as a dict to the `params` keyword. So both terms are equal::

   resp = client.get("library", response_groups="...", num_results=20)
   resp = client.get(
       "library",
       params={
           "response_groups"="...",
           "num_results"=20
       }
   )

The external Audible API awaits a request body in JSON format. You have to
provide the body as a dict to the Client. The Client converts and sends them
in JSON style to the API. You can send them like so::

   resp = client.post(
       "wishlist",
       body={"asin": ASIN_OF_BOOK_TO_ADD}
   )

The Audible API responses are in JSON format. The client converts them to a
and output them as a Python dict.

.. note::

   For all known API endpoints take a look at :ref:`api_endpoints`.

Show/Change Marketplace
-----------------------

The currently selected marketplace can be shown with::
   
    client.marketplace

The marketplace can be changed with::

   client.switch_marketplace(COUNTRY_CODE)

Username/Userprofile
--------------------

To get the profile for the user, which authentication data are used you 
can do this::

   user_profile = client.get_user_profile()

   # or from an Authenticator instance
   auth.refresh_access_token()
   user_profile = auth.user_profile()

To get the username only::

   user_name = client.user_name

Switch User
-----------

If you work with multiple users you can do this::

   # instantiate 1st user
   auth = audible.Authenticator.from_file(FILENAME)

   # instantiate 2nd user
   auth2 = audible.Authenticator.from_file(FILENAME2)

   # instantiate client with 1st user
   client = audible.AudibleAPI(auth)
   print(client.user_name)

   # now change user with auth2
   client.switch_user(auth2)
   print(client.user_name)
   
   # optional set default marketplace from 2nd user
   client.switch_user(auth2, switch_to_default_marketplace=True)

Misc
----

The underlying Authenticator can be accessed via the `auth` attribute.

Authenticator classes
=====================

.. deprecated:: v0.5.0

   The ``LoginAuthenticator`` and the ``FileAuthenticator``

.. versionchanged:: v0.5.0

   The ``LoginAuthenticator`` and the ``FileAuthenticator`` now instantiate the
   the new :class:`Authenticator` instead a class of its own. 

.. versionadded:: v0.5.0

   The :class:`Authenticator` with the  classmethods ``from_file`` and 
   ``from_login``

The :meth:`Authenticator.from_login` classmethod is used to authorize 
an user and then authenticate requests with the received data. The 
:meth:`Authenticator.from_file` classmethod is used to load
previous saved authentication data.

With an Authenticator you can:

- Save credentials to file with ``auth.to_file()``
- Register a device with ``auth.register_device()`` after a fresh authorization.
- Deregister a previously registered device with ``auth.deregister_device()``.
- Relogin a previously authorized user with ``auth.re_login()`` when 
  the master access token is expired. Don't use this after a device registration.
- Refresh a access token from previously registered device with 
  ``auth.refresh_access_token()``.
- Get user profile with ``auth.user_profile()``. Needs a valid access token.

To check if a access token is expired you can call::

   auth.access_token_expired

Or to check the time left before token expires::

   auth.access_token_expires

Activation Bytes
================

.. versionadded:: v0.4.0

   Get activation bytes

.. versionadded:: v0.5.0

   the ``extract`` param

To retrieve activation bytes an authentication :class:`Authenticator` is needed.

The Activation bytes can be obtained like so::

   activation_bytes = auth.get_activation_bytes()

   # the whole activation blob can fetched with
   auth.get_activation_bytes(extract=False)

The activation blob can be saved to file too::

   activation_bytes = auth.get_activation_bytes(FILENAME)

.. attention::

   Please only use this for gaining full access to your own audiobooks for 
   archiving / converson / convenience. DeDRMed audiobooks should not be uploaded
   to open servers, torrents, or other methods of mass distribution. No help
   will be given to people doing such things. Authors, retailers, and
   publishers all need to make a living, so that they can continue to produce
   audiobooks for us to hear, and enjoy. Don't be a parasite.

PDF Url
=======

PDF urls received by the Audible API don't work anymore. Authentication data
are missing in the provided link. As a workaround you can do::

   import audible
   import httpx
   
   asin = ASIN_FROM_BOOK
   auth = audible.Authenticator.from_file(...)  # or Authenticator.from_login
   tld = auth.locale.domain

   with httpx.Client(auth=auth) as client:
       resp = client.head(
            f"https://www.audible.{tld}/companion-file/{asin}"
       )
       url = resp.url

Decrypting license
==================

Responses from the :http:post:`/1.0/content/(string:asin)/licenserequest`
endpoint contains the encrypted license (voucher).

To decrypt the license response you can do::

   from audible.aescipher import decrypt_voucher_from_licenserequest
   
   auth = YOUR_AUTH_INSTANCE
   lr = RESPONSE_FROM_LICENSEREQUEST_ENPOINT
   dlr = decrypt_voucher_from_licenserequest(auth, lr)

.. attention::

   Please only use this for gaining full access to your own audiobooks for 
   archiving / converson / convenience. DeDRMed audiobooks should not be uploaded
   to open servers, torrents, or other methods of mass distribution. No help
   will be given to people doing such things. Authors, retailers, and
   publishers all need to make a living, so that they can continue to produce
   audiobooks for us to hear, and enjoy. Don't be a parasite.
