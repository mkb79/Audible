=================================
Load and Save authentication data
=================================

Unencrypted Load/Save
=====================

Authentication data can be saved any time to file like so::

   auth.to_file(FILENAME, encryption=False)

And can then be reused later like so::

   auth = audible.Authenticator.from_file(FILENAME)

.. note::

   The provided `FILENAME` is set as default when loading from or save to file.
   Simply run ``auth.to_file()`` to overwrite the previous loaded file.

Encrypted Load/Save
===================

This Client supports file encryption. The encryption algorithm used is
symmetric AES in cipher-block chaining (CBC) mode. Currently json and bytes
style output are supported.

Authentication data can be saved any time to encrypted file in json style like so::

   auth.to_file(
       FILENAME,
       PASSWORD,
       encryption="json"
   )

Or in bytes style like so::

   auth.to_file(
       FILENAME,
       PASSWORD,
       encryption="bytes"
   )

When loading data from file, encryption style is auto detected. These files can
be loaded like so::

   auth = audible.Authenticator.from_file(
       FILENAME,
       PASSWORD
   )

.. note::

   Authenticator sets the last `FILENAME`, `PASSWORD` and `ENCRYPTION` as
   default when loading from or save to file. Simply run ``auth.to_file()``
   to overwrite the previous loaded file with these settings.

Which data are saved?
=====================

If you save authentication data following data will be stored to file after an
authorization:

- website_cookies
- access_token
- locale_code (our country code)
- expires (access token)

In addition to above, following data will be stored after a device registration:

- refresh_token
- adp_token
- device_private_key
- store_authentication_cookie
- device_info
- customer_info

Advanced use of encryption/decryption
=====================================

When saving authentication data, additional options can be provided with
``auth.to_file(..., **kwargs)``. This data can be loaded with
``auth = audible.Authenticator.from_file(..., **kwargs)``.

Following options are supported:

- key_size (default = 32)
- salt_marker (default = b"$")
- kdf_iterations (default = 1000)
- hashmod (default = Crypto.Hash.SHA256)
    
`key_size` may be 16, 24 or 32. The key is derived via the PBKDF2 key derivation
function (KDF) from the password and a random salt of 16 bytes (the AES block
size) minus the length of the salt header (see below).

The hash function used by PBKDF2 is SHA256 per default. You can pass a
different hash function module via the `hashmod` argument. The module must
adhere to the Python API for Cryptographic Hash Functions (PEP 247).

PBKDF2 uses a number of iterations of the hash function to derive the key,
which can be set via the `kdf_iterations` keyword argumeent. The default number
is 1000 and the maximum 65535.

The header and the salt are written to the first block of the encrypted output
(bytes mode) or written as key/value pairs (dict mode). The header consist of
the number of KDF iterations encoded as a big-endian word bytes wrapped by
`salt_marker` on both sides. With the default value of `salt_marker = b'$'`,
the header size is thus 4 and the salt 12 bytes. The salt marker must be a
byte string of 1-6 bytes length. The last block of the encrypted output is
padded with up to 16 bytes, all having the value of the length of the padding.

In json style all values are written as base64 encoded string.

Remove encryption
=================

To remove encryption from file (or save as new file) simply load the encrypted
file with :meth:`audible.Authenticator.from_file` and save the data
unencrypted. If the `Authenticator` can't load your data, you can try::

   from audible.aescipher import remove_file_encryption

   remove_file_encryption(
       encrypted_file=FILENAME,
       decrypted_file=FILENAME,
       password=PASSWORD_FOR_ENCRYPTED_FILE
   )

