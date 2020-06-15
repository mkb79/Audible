=================
Register a Device
=================

Register
========

Clients with an `master` access token can register a new audible device. 
Clients are given an refresh token, RSA private key, adp_token and more 
useful credentials and informations after registration.

To register a new device after a successfully authentication you can 
call ``auth.register_device()``.

To authenticate and register a new device in one step you can do::

   auth = audible.LoginAuthenticator(
       username,
       password,
       locale=country_code,
       register=True)

Now requests to the audible API can be signed (authorized) using the 
provided RSA private key and adp_token. Request signing is fairly 
straight-forward and uses a signed SHA256 digest. Headers look like::

   x-adp-alg: SHA256withRSA:1.0
   x-adp-signature: AAAAAAAA...:2019-02-16T00:00:01.000000000Z,
   x-adp-token: {enc:...}

.. attention::

   Every registered device will add an entry to amazon device list. 
   Please register a new device only if neccessary. Best option is to 
   register device only once and then reuse (save/load) credentials.

Deregister
==========

Refresh token, RSA private key and adp_token are valid until deregister.

To deregister a device with client call ``auth.deregister_device()`` from
a previous registered `auth` instance. To deregister, a valid access token 
is needed. If access token is expired, it have to renew with ``auth.refresh_access_token()`` 
before deregister. 

To deregister all devices call ``auth.deregister_device(deregister_all=True)``.
This function is necessary to prevent hanging slots if you registered 
a device earlier but don‘t store the given credentials.
This also deregister all other devices such as a audible app on mobile 
devices.