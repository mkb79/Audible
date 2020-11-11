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
the audible/amazon web page using the httpx module. These are:

- sign request method (needs a device registration)
- bearer token method
- website cookies method

The default mode is used, when adding a Authenticator instance as a keyword 
argument to a httpx client. On default mode, the sign request auth method is preferred. 
If the sign method is not available, the bearer token auth method is choosen. If access 
token is not present or the access token is expired and no refresh token is found, 
a Exception will be raise. Here is a code example::

   import audible
   import httpx

   auth = audible.FileAuthenticator(...)  # or audible.LoginAuthenticator
   with httpx.Client(auth=auth) as client:
       r = client.get(...)

To make use of website cookies authentication, cookies have to be added as a 
cookies keyword argument to a httpx client. Cookies are limited to the scope of 
a top level domain (e.g. com, de, ...). In general case this is the top level 
domain for a country_code you have selected to login or register to. 
To get website cookies for another top level domain scope, you can call the 
method `set_website_cookies_for_country(country_code)` from  `auth` instance. 
Warning: present website cookies for another country code will be overriden. 
If you want to keep the new cookies, please make sure to save to file. 
Usually website cookies are only used to make authenticated requests to the 
audible or amazon web page. Here is a code example::

   import audible

   auth = audible.FileAuthenticator(FILENAME)

   auth.set_website_cookies_for_country("us")
   with httpx.Client(cookies=auth.website_cookies) as client:
       r = client.get("https://www.amazon.com/cpe/yourpayments/wallet?ref_=ya_d_c_pmt_mpo")
       print(r.text)

   auth.set_website_cookies_for_country("de")
   with httpx.Client(cookies=auth.website_cookies) as client:
       r = client.get("https://www.amazon.de/cpe/yourpayments/wallet?ref_=ya_d_c_pmt_mpo")
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

