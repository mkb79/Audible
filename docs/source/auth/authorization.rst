=====================
Authorization (Login)
=====================

Information
===========

Clients are authorized using OpenID. Once a client has successfully authorized
to Amazon, they are get an `master` access token and website cookies for
further authentication to Audible/Amazon.

An `master` access token can be used to register a new audible device or to
make *restricted* requests to the Audible API. The token expires after 60
minutes. After expiration you have to authorize again to obtain a new one.

.. _authorization:

Authorization
=============

For an example how to authorize please take a look at :ref:`hello_library`.

CAPTCHA
-------

Authorization currently requires answering a CAPTCHA. By default Pillow is used
to show captcha and an user prompt will be provided to enter your answer, which
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

If two-factor authentication (2FA) is activated a user prompt will be provided
using `input` to enter your one time password (OTP), which looks like::

   "OTP Code: "

A custom callback can be provided, like so::

   def custom_otp_callback():
    
       # Do some things to insert otp code

       return "My answer for otp code"

   auth = audible.Authenticator.from_login(
       ...
       otp_callback=custom_otp_callback
   )

If you have to enter a otp often and don't care about security you can use 
the `pyotp <https://pypi.org/project/pyotp/>`_ package with a custom callback
like so::

   from pyotp.totp import TOTP

   def otp_callback():
       secret = "YOUR-AMAZON-OTP-SECRET"
       secret = secret.replace(" ", "")
       otp = TOTP(secret)
       return str(otp.now())

CVF Code
--------

If 2FA is deactivated and amazon detects some security risks (too many logins
in short times, etc.) you will be asked for a verify code (CVF). In that case,
amazon sends you a Mail or SMS with a code, you have to enter here::

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

Some users report, that authorize to audible gives them an approval alert and
you will receive an email from amazon. Since audible v0.5 you will get an user
prompt which looks like::

   "Approval alert detected! Amazon sends you a mail."
   "Please press enter when you approve the notification."

Please approve the amazon email notification and press enter (or another key)
to proceed.

A custom callback can be provided, like so::

   def custom_approval_callback():
    
       # You can let python check for the received Amazon mail and 
       # open the approval link. The login function wait until
       # the callback function is executed. The returned value will be
       # ignored by the login function.
       

   auth = audible.Authenticator.from_login(
       ...
       approval_callback=custom_approval_callback
       )