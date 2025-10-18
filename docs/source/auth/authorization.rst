=====================
Authorization (Login)
=====================

Information
===========

Clients are authorized using OpenID in Authorization Code Flow with PKCE.
Once a client has successfully authorized to Amazon, they receive an
`authorization code` for device registration to Audible/Amazon.

.. _authorization:

Authorization
=============

For an example on authorization, please take a look at :doc:`../intro/quickstart`.

CAPTCHA
-------

.. versionadded:: v0.5.2

   Init cookies added to login function to prevent CAPTCHAs in most cases.

Authorization requires answering a CAPTCHA in some cases. By default Pillow is used
to show the CAPTCHA and a user prompt will be provided to enter your answer, which
looks like::

   Answer for CAPTCHA:

A custom callback can be provided (for example submitting the CAPTCHA to an
external service), like so::

   def custom_captcha_callback(captcha_url):

       # Do some things with the captcha_url ...
       # maybe you can call webbrowser.open(captcha_url)
       # or simply print out the captcha_url

       return "My answer for CAPTCHA"

   auth = audible.Authenticator.from_login(
       ...
       captcha_callback=custom_captcha_callback
   )

2FA (OTP Code)
--------------

If two-factor authentication (2FA) is activated, a user prompt will be provided
using `input` to enter your one-time password (OTP), which looks like::

   "OTP Code: "

A custom callback can be provided, like so::

   def custom_otp_callback():

       # Do some things to insert otp code

       return "My answer for otp code"

   auth = audible.Authenticator.from_login(
       ...
       otp_callback=custom_otp_callback
   )

If you have to enter an OTP often and don't care about security, you can use
the `pyotp <https://pypi.org/project/pyotp/>`_ package with a custom callback
like so::

   from pyotp.totp import TOTP

   def otp_callback():
       secret = "YOUR-AMAZON-OTP-SECRET"
       secret = secret.replace(" ", "")
       otp = TOTP(secret)
       return str(otp.now())

Another approach is to append the current OTP to the password.

CVF Code
--------

If 2FA is deactivated and Amazon detects some security risks (too many logins
in short times, etc.) you will be asked for a verify code (CVF). In that case,
Amazon sends you an email or SMS with a code, which you enter here::

   "CVF Code: "

A custom callback can be provided, like so::

   def custom_cvf_callback():

       # Do some things to insert cvf code

       return "My answer for cvf code"

   auth = audible.Authenticator.from_login(
       ...
       cvf_callback=custom_cvf_callback
   )

Approval Alert
--------------

Some users report that trying to authorize with Audible gives them an approval alert and an email from Amazon.
Since Audible v0.5 you will get a user prompt which looks like::

   "Approval alert detected! Amazon sends you a mail."
   "Please press enter when you approve the notification."

Please approve the email/SMS, and press any key to continue.

.. versionadded:: 0.5.1

   Provide a custom callback with ``approval_callback``

A custom callback can be provided, like so::

   def custom_approval_callback():

       # You can let Python check for the received Amazon mail and
       # open the approval link. The login function waits until
       # the callback function is executed. The returned value will be
       # ignored by the login function.


   auth = audible.Authenticator.from_login(
       ...
       approval_callback=custom_approval_callback
       )

Authorization with external browser or program logic
====================================================

.. versionadded:: v0.5.1

   Login with external browser or program logic

To handle the login with an external browser or program logic you can do the following::

   import audible

   auth = audible.Authenticator.from_login_external(locale=COUNTRY_CODE)

By default, this code prints out the login URL for the selected country code.
Paste this URL into a web browser or use it programmatically to authorize yourself.
You have to enter your credentials two times (because of missing init cookies).
First time, the password can be a random one.
Second time, you have to solve a CAPTCHA before you can submit the login form and
you must use your correct password.
After you log in, you will end in an error page (not found). This is correct.
Copy the URL from the address bar from your browser and paste the URL into the input
field of the Python code. It will look something like
"https://www.amazon.{domain}/ap/maplanding?...&openid.oa2.authorization_code=..."

.. note::
   If you have `playwright <https://pypi.org/project/playwright/>`_ installed and
   use the default ``login_url_callback``, a new browser is opened, where you can
   authorize to your account.

.. note::

   If you are using MacOS and have trouble inserting the login result URL, simply import the
   readline module in your script. See
   `#34 <https://github.com/mkb79/Audible/issues/34#issuecomment-766408640>`_.

Custom callback
---------------

A custom callback can be provided (for example open the URL in a web browser directly), like so::

   def custom_login_url_callback(login_url):

       # Do some things with the login_url ...
       # maybe you can call webbrowser.open(login_url)
       # or simply print out the login_url

       return "The postlogin url"

   auth = audible.Authenticator.from_login_external(
       ...
       login_url_callback=custom_login_url_callback
       )
