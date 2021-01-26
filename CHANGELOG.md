# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## Unreleased

### Misc

- Redesign Module documentation
- Rework description of audible-cli package in documentation

## [0.5.3] - 2020-01-25

### Added

- function `activation_bytes.fetch_activation_sign_auth`
- Spain marketplace

### Changed

- `activation_bytes.get_activation_bytes` uses the new `fetch_activation_sign_auth` function, if `signing` auth method is available. Otherwise activation bytes will be fetched the old way with a `player_token`.

## [0.5.2] - 2020-01-08

### Added

- Add initial cookies to login function to prevent captcha requests in most cases.

## [0.5.1] - 2020-01-05

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
