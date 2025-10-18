=================================
Load and Save authentication data
=================================

Unencrypted Load/Save
=====================

Authentication data can be saved at any time to a file like so::

   auth.to_file(FILENAME, encryption=False)

And can then be reused later like so::

   auth = audible.Authenticator.from_file(FILENAME)

.. note::

   The provided `FILENAME` is set as the default when loading from or saving to a file.
   Simply run ``auth.to_file()`` to overwrite the previously loaded file.

.. versionadded:: v0.7.1

   The :meth:`audible.Authenticator.to_dict` and :meth:`audible.Authenticator.from_dict` methods.

With :meth:`audible.Authenticator.to_dict` you can get the authentication data as a
dictionary. This enables you to implement your own save/load methods. Simply
use the :meth:`audible.Authenticator.from_dict` classmethod to load the data from
the dictionary.

Encrypted Load/Save
===================

This library supports file encryption. The encryption algorithm used is
symmetric AES in cipher-block chaining (CBC) mode. Currently JSON and bytes
style output are supported.

Authentication data can be saved at any time to an encrypted file in JSON style like so::

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

When loading data from a file, the encryption style is auto-detected. These files can
be loaded like so::

   auth = audible.Authenticator.from_file(
       FILENAME,
       PASSWORD
   )

.. note::

   Authenticator sets the last `FILENAME`, `PASSWORD` and `ENCRYPTION` as
   default when loading from or saving to a file. Simply run ``auth.to_file()``
   to overwrite the previously loaded file with these settings.

Which data are saved?
=====================

The following data will be stored:

- website_cookies
- access_token
- locale_code (your country_code)
- access_token expiration timestamp
- refresh_token
- adp_token
- device_private_key
- store_authentication_cookie
- device_info data
- customer_info data
- activation_bytes
- with_username (``True`` for pre-Amazon accounts, ``False`` otherwise)

.. versionadded:: 0.5.1

   Stores ``activation_bytes`` to file (if they were fetched before).

.. versionadded:: v0.8.0

   The ``with_username`` value

Advanced use of encryption/decryption
=====================================

When saving authentication data, additional options can be provided with
``auth.to_file(..., **kwargs)``. This data can be loaded with
``auth = audible.Authenticator.from_file(..., **kwargs)``.

The following options are supported:

- key_size (default = 32)
- salt_marker (default = b"$")
- kdf_iterations (default = 1000)
- hashmod (default = Crypto.Hash.SHA256)

`key_size` may be 16, 24 or 32. The key is derived via the PBKDF2 key derivation
function (KDF) from the password and a random salt of 16 bytes (the AES block
size) minus the length of the salt header (see below).

The hash function used by PBKDF2 is SHA256 by default. You can pass a
different hash function module via the `hashmod` argument. The module must
adhere to the Python API for Cryptographic Hash Functions (PEP 247).

PBKDF2 uses a number of iterations of the hash function to derive the key,
which can be set via the `kdf_iterations` keyword argument. The default number
is 1000 and the maximum is 65535.

The header and the salt are written to the first block of the encrypted output
(bytes mode) or written as key/value pairs (dict mode). The header consists of
the number of KDF iterations encoded as big-endian word bytes wrapped by
`salt_marker` on both sides. With the default value of `salt_marker = b'$'`,
the header size is thus 4 bytes and the salt is 12 bytes. The salt marker must be a
byte string of 1-6 bytes length. The last block of the encrypted output is
padded with up to 16 bytes, all having the value of the length of the padding.

In JSON style, all values are written as base64 encoded strings.

Remove encryption
=================

To remove encryption from a file (or save as a new file) simply load the encrypted
file with :meth:`audible.Authenticator.from_file` and save the data
unencrypted. If the `Authenticator` can't load your data, you can try::

   from audible.aescipher import remove_file_encryption

   remove_file_encryption(
       encrypted_file=FILENAME,
       decrypted_file=FILENAME,
       password=PASSWORD_FOR_ENCRYPTED_FILE
   )
