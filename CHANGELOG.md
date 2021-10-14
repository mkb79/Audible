# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## Unreleased

### Bugfix

- Fix a bug when searching for "resend-approval-link" in login page

### Changed

- switched to `auth_code_flow` when login (gives an auth code instead of an access token for security purposes)
- `Authenticator.from_login` and `Authenticator_from_login_external` now always register a new device

### Misc

- Correct documentation
- Update example download_books_aaxc.py

### Remove

- `LoginAuthenticator` and `FileAuthenticator`
- `Authenticator.register_device`, `Authenticator.re_login` and `Authenticator.re_login_external`

## [0.5.5] - 2021-07-22

### Misc

- switch from httpx 0.16.x to 0.18.x

### Added

- logging error messages during login

### Changed

- extend allowed chars by email check during login
- instead of raising an exception, invalid email will now be logged as warning

### Misc

- Add description to the docs, to handling 2FA

## [0.5.4] - 2021-02-28

### Added

- Provide a custom serial when login
- Login with Audible username instead of Amazon account for US, UK and DE
  markteplace

### Bugfix

- register a device on Australian marketplace

### Misc

- Redesign Module documentation
- Rework description of audible-cli package in documentation

## [0.5.3] - 2021-01-25

### Added

- function `activation_bytes.fetch_activation_sign_auth`
- Spain marketplace

### Changed

- `activation_bytes.get_activation_bytes` uses the new `fetch_activation_sign_auth` function, if `signing` auth method is available. Otherwise activation bytes will be fetched the old way with a `player_token`.

## [0.5.2] - 2021-01-08

### Added

- Add initial cookies to login function to prevent captcha requests in most cases.

## [0.5.1] - 2021-01-05

### Added

- Fetched activation bytes (with ``extract=True`` argument) will be stored to ``activation_bytes`` attribute of Authenticator class instance for now. Ignore existing activation bytes and force refresh with ``auth.get_activation_bytes(force_refresh=True)``
- ``activation_bytes`` will be loaded from and save  to file. Saved auth files are **not backward compatible** to previous audible versions so keep old files save.
- Add ``Client.raw_request`` and ``AsyncClient.raw_request`` method.
- Provide a custom Callback with ``approval_callback`` keyword argument when login.
- Add classmethod ``Authenticator.from_login_external`` and method ``Authenticator.re_login_external``.
- Add ``login_external`` function to login.py

### Misc

- Add description how to use pyotp with custom otp callback to docs
- Add description how to use login external to docs

## [0.5.0] - 2020-12-07

### Added

- Added support to output the whole activation blob instead of the extracted activation bytes with `get_activation_bytes(extract=False, ...)`.
- Added support to fetch website cookies for another country with `Authenticator.set_website_cookies_for_country`.
- Added `Client.put` and `AsyncClient.put`.
- Added support to solve approval alerts during login

### Changed

- The `FileAuthenticator` has been deprecated, use classmethod `Authenticator.from_file` instead.
- The `Authenticator` don't inherit from MutableMapping anymore
- The `Authenticator` sets allowed instance attributes at creation to `None`, not allowed attributes will raise an Exception
- The `LoginAuthenticator` has been deprecated, use  classmethod `Authenticator.from_login` instead.
- Changed internal code base for encryption and decryption metadata. Moved the related code to `metadata.py`.

### Remove

- deprecated `AudibleAPI`

### Misc

- Added more docstrings and type hints to code base
- Added support to install Sphinx documentation dependencies with `pip install audible[docs]`.
- Added a guide to use authentication with [Postman](https://www.postman.com).
- Rework documentation.
- Added `.readthedocs.yml` config file
- Added module description (autodoc) to docs
- Uses `httpx` 0.16.* for now

## [0.4.4] - 2020-10-25

### Bugfix

- Set `padding="none"` when decrypting license voucher 
