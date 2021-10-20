=====================
Authorization (Login)
=====================

Information
===========

Clients are authorized using OpenID in Authorization Code Flow with PKCE. 
Once a client has successfully authorized to Amazon, they are get an 
`authorization code` for device registration to Audible/Amazon.

.. _authorization:

Authorization
=============

For an example how to authorize please take a look at :ref:`hello_library`.

CAPTCHA
-------

.. versionadded:: v0.5.2

   Init cookies added to login function to prevent CAPTCHAs in most cases.

Authorization requires answering a CAPTCHA in some cases. By default Pillow is used
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

Another approach for submit the OTP is to append the current OTP to the password.

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

.. versionadded:: 0.5.1

   Provide a custom callback with ``approval_callback``

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

Authorization with external browser or program logic
====================================================

.. versionadded:: v0.5.1

   Login with external browser or program logic

To handle the login with a external browser or program logic you can do the following::

   import audible
   
   auth = audible.Authenticator.from_login_external(locale=COUNTRY_CODE)

By default, this code print out the login url for the selected country code. Now you have
to copy and paste this code into a webbrowser (or a custom program) and authorize yourself. 
You have to enter your credentials two times (because of missing init cookies). 
On first time, the password can be a random one.
On second time, you have to solve a captcha before you can submit the login form with your 
correct password.
After authorize successfully you will end in an error page (not found). This is correct. 
Please copy the url from the address bar from your browser and paste the url to the input 
field of the python code. This url looks like 
"https://www.amazon.{domain}/ap/maplanding?...&openid.oa2.authorization_code=..."

.. note::

   If you are using MacOS and have trouble insert the login result url, simply import the 
   readline module in your script. See
   `#34 <https://github.com/mkb79/Audible/issues/34#issuecomment-766408640>`_.

Custom callback
---------------

A custom callback can be provided (for example open the url in a webbrowser directly), like so::

   def custom_login_url_callback(login_url):
    
       # Do some things with the login_url ... 
       # maybe you can call webbrowser.open(login_url)
       # or simply print out the login_url

       return "The postlogin url"

   auth = audible.Authenticator.from_login_external(
       ...
       login_url_callback=custom_login_url_callback
       )

