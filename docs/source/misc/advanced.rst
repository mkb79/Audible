==============
Advanced Usage
==============

AudibleAPI class
================

Here are some things to be known about the ``AudibleAPI`` class.


Some informations
-----------------

The ``AudibleAPI`` class has the following methods to send requests to the
external API:

- get
- post
- delete

The external Audible API offers currently two API versions, `0.0` and 
`1.0`. ``AudibleAPI`` use the newest `1.0` by default. The older API 
version can be choosen with::

   resp, _ = client.get(..., api_version="0.0")

But usually it's not needed.

Make requests
-------------

The response for all requests with this Client is a tuple with 
response text and the raw response object. The raw response 
object is only needed for further informations if somethings 
getting wrong. If you only want the response text you can do ::

   response_text, _ = client.get(...)

.. versionadded:: v0.3.1a0
   The *return_raw* parameter

.. code-block::

   response_text = client.get(..., return_raw=False)

For known api endpoints take a look at :ref:`api_endpoints`.

If you want to request endpoint `GET /1.0/library` you have to use 
class method `get`. The api version in this case is "1.0", so you 
don't have to provide them. The path is "library". This endpoint 
supports various params, they can be provided as keyword argument. 

Here are some examples how to use the endpoints with this client:

GET /1.0/library::

   resp, _ = client.get(
      "library",
      num_results=999,
      response_groups="media, price")

POST /1.0/wishlist::

   resp, _ = client.post(
       "wishlist",
       body={"asin": "B002V02KPU"}
   )

DELETE /1.0/wishlist/%{asin}::

   resp, _ = client.delete(
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

Misc
----

The underlying Authenticator class can be accessed via the auth attribute.

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