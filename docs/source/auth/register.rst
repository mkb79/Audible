=========================
Register a Audible device
=========================

Register
========

Clients are obtaining additional authentication data and information after
registration a "virtual" Audible device.

To authorize and register a new device you can do::

   auth = audible.Authenticator.from_login(
       username,
       password,
       locale=country_code,
       with_username=False,
   )

This will authorize you to your account and register an Audible device.

New registrations use a random 40-character serial containing ASCII letters and
digits, together with the default Audible for iPhone profile (app ``4.60``,
iOS ``26.2``, software version ``46000856``). An explicitly supplied serial is
preserved, including serials from older registrations.

Updating the package does not change an existing device registration. To use
the updated profile, register a new device and save its credentials.

.. important::

   Every device registration will be shown on the Amazon devices list. So only
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
