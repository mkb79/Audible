=========================
Register a Audible device
=========================

Register
========

Clients obtain their authentication data by registering a "virtual"
Audible device. Logging in and registering are one step::

   login = audible.create_login(country_code)
   prompt = login.start()
   print(f"Open {prompt.verification_url} and enter the code {prompt.public_code}")
   auth = login.wait()

The returned :class:`audible.Authenticator` holds the credentials of the new
device. Pre-Amazon accounts sign in through a browser instead; see
:ref:`authorization` for both ways.

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
