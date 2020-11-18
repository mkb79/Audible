=========================
Register a Audible device
=========================

Register
========

To deal with the limitations if working with *authorized only* clients
(expiration and restricted API calls) you can register a audible device.
Clients are obtaining additional authentication data and information after
registration.

To register a new device you can call ``auth.register_device()`` after a
successfully authorization.

To authorize and register a new device in one step you can do::

   auth = audible.Authenticator.from_login(
       username,
       password,
       locale=country_code,
       register=True)

.. note::

   Only an `master` access token from a fresh authorization can register a new
   device. An access token from a previous registered device will not work.

.. important::

   Every device registration will be shown on the amazon devices list. So only
   register once and save your credentials or deregister the device before you
   close your session.

Deregister
==========

Authentication data obtained by a device registration are valid until
deregister. Call ``auth.deregister_device()`` to deregister the current used 
device.

Call ``auth.deregister_device(deregister_all=True)`` to deregister **ALL**
Audible devices. This function is helpful to remove hanging slots. This can
happens if you registered a device and forgot to store the given authentication
data or to deregister. This also deregister all other devices such as an
Audible app on mobile devices. If you only want to remove one registration you
can also open the amazon devices list on the the amazon website.

.. important::

   Deregister needs an valid access token. The authentication data from a
   device registration contains a refresh token. With these token, an access
   token can be renewed with ``auth.refresh_access_token()``.
