==============
Advanced Usage
==============

Client classes
==============

Here are some things to be known about the ``Client`` and 
the ``AsyncClient`` class.


Some informations
-----------------

Both client classes have the following methods to send requests 
to the external API:

- get
- post
- delete

The external Audible API offers currently two API versions, `0.0` and 
`1.0`. The Client use the newest `1.0` by default::

   resp = client.get("library")

Long term can be used too::

   resp = client.get("1.0/library")

The older API version can be choosen with::

   resp = client.get(path="0.0/library/books")

But usually old API is not needed anymore.

Make requests
-------------

The response for all requests with this Client is a dict.

For known api endpoints take a look at :ref:`api_endpoints`.

If you want to request endpoint `GET /1.0/library` you have to use 
class method `get`. The api version in this case is "1.0", so you 
don't have to provide them. The path is "library". This endpoint 
supports various params, they can be provided as keyword argument. 

Here are some examples how to use the endpoints with this client:

GET /1.0/library::

   resp = client.get(
      "library",
      num_results=999,
      response_groups="media, price")

POST /1.0/wishlist::

   resp = client.post(
       "wishlist",
       body={"asin": "B002V02KPU"}
   )

DELETE /1.0/wishlist/%{asin}::

   resp = client.delete(
       "wishlist/B002V02KPU"
   )

Show/Change Marketplace
-----------------------

The currently selected marketplace can be displayed with::
   
    client.marketplace

The marketplace can be changed with::

   client.switch_marketplace(CountryCode)

Username/Userprofile
--------------------

To get the profile for the user, which credentials are used you 
can do this::

   user_profile = client.get_user_profile()

To get the username only::

   user_name = client.user_name

Change User
-----------

If you work with multiple users you can do this::

   # instantiate 1st user
   auth = audible.FileAuthenticator(FILENAME)

   # instantiate 2nd user
   auth2 = audible.FileAuthenticator(FILENAME2)

   # instantiate client with 1st user
   client = audible.AudibleAPI(auth)
   print(client.user_name)

   # now change user with auth2
   client.switch_user(auth2)
   print(client.user_name)
   
   # optional set default marketplace for 2nd user
   client.switch_user(auth2, switch_to_default_marketplace=True)

Misc
----

The underlying Authenticator class can be accessed via the `auth` attribute.

Authenticator classes
=====================

There are two Authenticator classes. The ``LoginAuthenticator`` 
and the ``FileAuthenticator``. Both derive from ``BaseAuthenticator``. 

The ``LoginAuthenticator`` is used to authenticate a user at init 
process. The ``FileAuthenticator`` is used to load previous stored 
credentials from file at init. 

The Authenticator classes authorize API requests with sign method 
(device registration is needed) or access token (authentication 
is needed). Sign method is the preferred method. There are some 
API restriction with access token authorization. 

With a Authenticator class instance you can:

- Save credentials to file with ``auth.to_file()``
- Register a new device with ``auth.register_device()``. This needs a 
  master access token. A access token from registered device can't be used.
- Deregister a previously registered device with 
  ``auth.deregister_device()``. This can't be done with a master access 
  token.
- Relogin a previously authenticated user with ``auth.re_login()`` when 
  the master access token is expired. A Authentication gives no refresh 
  token.
- Refresh a access token from previously registered device with 
  ``auth.refresh_access_token()``.

To check if a access token is expired you can call::

   auth.access_token_expired

Or to check the time left before token expires::

   auth.access_token_expires

Auth methods and auth flow
--------------------------

The Authenticator classes supports multiple methods of authentication to the API and/or 
the audible/amazon web page. These are:

- sign request method (needs a device registration)
- bearer token method
- website cookies method

By default, the sign request method is choosen. If this method is not available (missing 
adp token and device key from registrstion process), bearer token method is choosen. If 
no access token is present or the access token is expired and no refresh token is found, 
a Exception will be raise.

.. versionadded:: v0.5.0
   The `auth_mode` header to control the auth flow

To control the auth flow, the `auth_mode` header can be used. The `auth_mode` header 
can have the following values (they have be comma separated with or without a whitespace):

- `default`, must be standalone when provided, instead of providing the `default` 
  auth_mode you can left the header
- `none`, must be standalone when provided, deactivates all auth methods
- `signing`, applies the sign request method to the request
- `bearer`, applies the bearer token method to the request
- `cookies`, applies the website cookies method to the request, cookies are limited 
  to one specific tld range (e.g. com, de, ...). These range are set during login or
  device registration (country_code). To get new website cookies for a specific tld 
  range you can call the method `set_website_cookies_for_country(country_code)` from 
  `auth` instance. Warning: present website cookies for another country code will be 
  overriden. If you want to keep the new cookies, please make sure to save to file.

Usually the `auth_method` header will be used to make authenticate requests to the 
audible or amazon web page with cookies. You can do this with this example code::

   import audible

   auth = audible.FileAuthenticator(FILENAME)
   headers = {"auth_mode": "cookies"}

   with httpx.Client(auth=auth, headers=headers) as client:
       r = client.get("https://www.amazon.com/cpe/yourpayments/wallet?ref_=ya_d_c_pmt_mpo")
       print(r.text)

Activation Bytes
================

Since v0.4.0 this app can get activation bytes. 

To retrieve activation bytes an authentication via 
:class:`LoginAuthenticator` or :class:`FileAuthenticator` is 
needed.

With an auth instance, Activation bytes can be obtained like so::

   activation_bytes = auth.get_activation_bytes()

The activation blob can be saved to file too::

   activation_bytes = auth.get_activation_bytes(filename)

