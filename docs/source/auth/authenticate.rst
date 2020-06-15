==============
Authentication
==============

Informations
============

Clients are authenticated using OpenID. Once a client has 
successfully authenticated with Amazon, they are given an 
`master` access token for further authorization to 
Audible/Amazon.

A `master` access token can be used to register a new audible 
device or to make authorized requests to the audible API. The
token expires after 60 minutes. Authenticate again to retrieve 
a new one. 

Authenticate
============

To authenticate with amazon you can do::

   import audible
   
   auth = audible.LoginAuthenticator(
       username,
       password,
       locale=country_code,
       register=False)

.. note::

   For available country codes take a look at :ref:`country_codes`. 

.. _captcha:

CAPTCHA
-------

Logging in currently requires answering a CAPTCHA. By default 
Pillow is used to show captcha and user prompt will be provided 
using `input`, which looks like::

   Answer for CAPTCHA:

If Pillow can't display the captcha, the captcha url will be printed.

A custom callback can be provided (for example submitting the CAPTCHA 
to an external service), like so::

   def custom_captcha_callback(captcha_url):
    
       # Do some things with the captcha_url ... 
       # maybe you can call webbrowser.open(captcha_url)

       return "My answer for CAPTCHA"

   auth = audible.LoginAuthenticator(
       ...
       captcha_callback=custom_captcha_callback
   )

2FA (OTP Code)
--------------

If 2-factor-authentication is activated a user prompt will be provided 
using `input`, which looks like::

   "OTP Code: "

A custom callback can be provided, like so::


   def custom_otp_callback():
    
       # Do some things to insert otp code

       return "My answer for otp code"

   auth = audible.LoginAuthenticator(
       ...
       otp_callback=custom_otp_callback
   )

CVF Code
--------

If amazon detects some issues (too many logins in short times, etc.) 
and 2FA is deactivated, amazon asks for a CVF verify code. in this 
cases, amazon sends a Mail or SMS with a code, you have to enter here::

   "CVF Code: "

A custom callback can be provided, like so::

   def custom_cvf_callback():
    
       # Do some things to insert cvf code

       return "My answer for cvf code"

   auth = audible.LoginAuthenticator(
       ...
       cvf_callback=custom_cvf_callback
   )