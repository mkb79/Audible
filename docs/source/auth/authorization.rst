=====================
Authorization (Login)
=====================

.. _authorization:

Overview
========

Logging in and registering a new "virtual" Audible device are one step.
Once it has finished, an :class:`audible.Authenticator` holds the
credentials of the new device. Save them and reuse them instead of
registering again: every registration shows up in the device list of the
account.

How the login works depends on the kind of account:

- **Amazon accounts** register with a device code, see
  :class:`audible.login.DeviceCodeLogin`.
- **Pre-Amazon accounts** sign in with an Audible username. They exist on
  the DE, US and UK marketplaces only and sign in through a browser, see
  :class:`audible.login.ExternalLogin`.

:func:`audible.create_login` returns the matching login for the account
type. It sends no request; your code starts the login. The library never
prints, reads input or opens a browser. Showing the code or the URL to the
user is up to the application.

Amazon accounts
===============

.. code-block:: python

   import audible

   login = audible.create_login(COUNTRY_CODE)
   prompt = login.start()
   print(f"Open {prompt.verification_url} and enter the code {prompt.public_code}")

   auth = login.wait()
   auth.to_file(FILENAME)

:meth:`~audible.login.DeviceCodeLogin.start` creates a code pair. The user
opens the verification page on any device, for example a phone, signs in to
Amazon there and enters the code. Meanwhile
:meth:`~audible.login.DeviceCodeLogin.wait` asks Amazon, in the interval
Amazon requested, whether the code was confirmed. As soon as it is, Amazon
answers with the credentials of the newly registered device and ``wait()``
returns the authenticator.

A code stays valid for ``prompt.expires_in`` seconds. If nobody confirms it
in time, ``wait()`` raises :exc:`~audible.exceptions.LoginExpiredError`.

.. note::

   The device-code login has been confirmed on the German and French
   marketplaces. Other marketplaces use the same requests but have not been
   tested yet.

Status and non-blocking use
---------------------------

``wait()`` blocks until the login has ended. To keep a program responsive,
drive the login yourself or use the ``async_`` methods.

``login.status`` tells where a login stands, as a
:class:`~audible.login.LoginStatus`: ``PENDING``, ``FINISHED``, ``FAILED``,
``EXPIRED`` or ``ABORTED``. Reading it never sends a request.
:meth:`~audible.login.DeviceCodeLogin.poll` sends at most one request, and
only when the next attempt is due; it never sleeps. That makes it suitable
for a GUI timer or a status endpoint of a web application:

.. code-block:: python

   import time

   from audible.login import LoginStatus

   login = audible.create_login(COUNTRY_CODE)
   prompt = login.start()
   show(prompt)

   while login.status is LoginStatus.PENDING:
       time.sleep(login.next_poll_delay)
       login.poll()

   auth = login.result()

:meth:`~audible.login.DeviceCodeLogin.result` never blocks either. Before
the login has ended, it raises :exc:`~audible.exceptions.LoginStateError`;
if the login failed, expired or was cancelled, it raises the error that
ended it.

With asyncio, every method that talks to the network has an ``async_``
counterpart:

.. code-block:: python

   login = audible.create_login(COUNTRY_CODE)
   prompt = await login.async_start()
   show(prompt)

   auth = await login.async_wait()

To do other work while the user confirms the code, run ``async_wait()`` as a
task and read ``login.status`` in the meantime:

.. code-block:: python

   task = asyncio.create_task(login.async_wait())
   ...
   if login.status is LoginStatus.FINISHED:
       auth = login.result()

``wait(timeout=...)`` and ``async_wait(timeout=...)`` raise
:exc:`TimeoutError` when the timeout passes first. The login stays pending
and can be waited for again. :meth:`~audible.login.DeviceCodeLogin.cancel`
ends a pending login with the status ``ABORTED``; cancelling the task that
runs ``async_wait()`` does the same. So does interrupting ``start()`` or
``complete()``, for example with Ctrl+C or by cancelling the awaiting task,
because the request may already have reached Amazon.

Only one caller at a time should drive a login, while any number of callers
may read its status. A login lives in memory only: if the program exits
before the code is confirmed, start a new login.

.. important::

   A registration request already sent cannot be taken back. Should Amazon
   register the device after the login was cancelled, the device appears in
   the device list of the account without credentials. Remove it there.

Several devices at once
-----------------------

Every login is an object of its own, without shared state. Several logins
can run at the same time, as asyncio tasks or in threads:

.. code-block:: python

   logins = [audible.create_login(code) for code in ("de", "fr", "uk")]
   prompts = await asyncio.gather(*(login.async_start() for login in logins))
   show(prompts)

   auths = await asyncio.gather(*(login.async_wait() for login in logins))

A waiting login always ends: every request has a timeout of 25 seconds, and
``wait()`` returns once the code has expired, at the latest after the request
in progress. ``cancel()`` wakes a sleeping ``wait()`` or ``async_wait()`` at
once, also from another thread. To use an httpx client of your own, create
:class:`~audible.login.DeviceCodeLogin` or
:class:`~audible.login.ExternalLogin` directly and pass it as ``client`` or
``async_client``. It is used as it is; give it a timeout as well, or a
stalled connection blocks the login.

While polling, the login retries overload answers (HTTP 429 and 5xx) and
network errors with a growing delay. Creating the code is not retried: if
Amazon refuses it, ``start()`` raises
:exc:`~audible.exceptions.LoginFailedError`.

Pre-Amazon accounts
===================

.. code-block:: python

   import audible

   login = audible.create_login(COUNTRY_CODE, with_username=True)
   prompt = login.start()
   print(f"Open {prompt.login_url} in a browser and sign in.")

   auth = login.complete(input("URL after signing in: "))
   auth.to_file(FILENAME)

After signing in, the browser shows a "page not found" error. That is
expected: the URL in the address bar starts with
``https://www.audible.<tld>/ap/maplanding`` and carries the authorization
code. :meth:`~audible.login.ExternalLogin.complete` checks the URL,
registers the device and returns the authenticator. A URL that is not this
page raises :exc:`ValueError` and leaves the login pending, so the user can
try again. With asyncio, use ``await login.async_complete(url)``.

Browser automation is not part of the library. An application can open
``prompt.login_url`` with a tool such as
`playwright <https://pypi.org/project/playwright/>`_ itself and pass the
final URL to ``complete()``.

.. note::

   The URL is long, often more than 1,000 characters. On macOS, ``input()``
   cuts a pasted line off at 1,024 characters unless the ``readline`` module
   has been imported (``import readline``). See
   `#34 <https://github.com/mkb79/Audible/issues/34#issuecomment-766408640>`_.
   An application can also take the URL from a text field or a file.

The authorization code in the URL is valid once. If ``complete()`` has sent
it and the registration failed, start a new login.

The browser sign-in exists for pre-Amazon accounts only. Amazon accounts
register with the device code; a URL from ``www.amazon.<tld>`` is refused.

Errors
======

All login errors derive from :exc:`audible.exceptions.LoginError`:

- :exc:`~audible.exceptions.LoginFailedError`: Amazon or Audible rejected
  the login or answered unexpectedly, or the network failed. Its
  ``status_code`` and ``error_code`` attributes carry the details of a
  rejecting response.
- :exc:`~audible.exceptions.LoginExpiredError`: the device code expired
  before it was confirmed.
- :exc:`~audible.exceptions.LoginAbortedError`: the login was cancelled.
- :exc:`~audible.exceptions.LoginStateError`: a method was called in a state
  that does not allow it, for example ``poll()`` before ``start()``.

Migrating from ``from_login``
=============================

Up to audible 0.13, ``Authenticator.from_login`` logged in with username
and password and answered CAPTCHA, OTP, CVF and approval prompts through
callbacks, while ``Authenticator.from_login_external`` signed in through
a browser. Both are gone, together with the modules ``audible.register`` and
``audible.metadata`` and the dependencies ``beautifulsoup4`` and ``Pillow``.
Amazon now asks for password, OTP or CAPTCHA on its own sign-in page.

- ``Authenticator.from_login(username, password, locale=...)`` and
  ``Authenticator.from_login_external(locale=...)`` for an Amazon account:
  ``audible.create_login(locale)``, then the steps under
  `Amazon accounts`_.
- ``from_login(..., with_username=True)`` and
  ``from_login_external(..., with_username=True)``:
  ``audible.create_login(locale, with_username=True)``, then the steps under
  `Pre-Amazon accounts`_.
- ``audible.register.deregister(...)``:
  :meth:`~audible.auth.Authenticator.deregister_device`.

An :class:`~audible.auth.Authenticator` now comes from a finished login,
from :meth:`~audible.auth.Authenticator.from_file` or from
:meth:`~audible.auth.Authenticator.from_dict`. Authentication files saved by
earlier versions load unchanged with
:meth:`~audible.auth.Authenticator.from_file`.
