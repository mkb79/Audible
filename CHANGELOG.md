# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## Unreleased

## [0.10.0] - 2024-09-26

### Bugfix

- Fix `autodetect_locale` function

### Misc

- Drop support for Python 3.8 and 3.9
- Add support for Python 3.12

## [0.9.1] - 2023-09-27

## Bugfix

- Fix login issues on brazilian marketplace.
- Fix a `RecursionError` which occurs when checking the length of an `Authenticator` instance.

## [0.9.0] - 2023-09-27

## Bugfix

- Multiple fixes for XXTEA encryption/decryption in metadata module.

### Added

- Add brazilian marketplace.
- Login function now checks for a `verification-code-form` tag in login HTML page.

### Changes

- Drop support for Python 3.7.

### Misc

- First step to refactor code.
- Switch project to poetry.
- Using nox and ruff for tests and linting.

## [0.8.2] - 2022-05-25

### Changed

- Allow httpx v0.23.x to fix a bug in httpx

## [0.8.1] - 2022-04-20

### Bugfix

- fix a bug in `Client.delete` and `AsyncClient.delete` method

## [0.8.0] - 2022-04-11

### Added

- full support of pre-Amazon accounts (e.g. refresh access token, deregister device)
- `Client` and `AsynClient` now accepts session kwargs which are bypassed to the underlying httpx Client
- a `respone_callback` can now be set to `Client` and `AsyncClient` class to allow custom preparation of response output
- An absolut url (e.g. https://cde-ta-g7g.amazon.com/FionaCDEServiceEngine/sidecar) can now be passed to a client `get`, `post`, `delete` and `put` method as the `path` arg. So in most cases the client `raw_request` method is not needed anymore.

### Changed

- rename (and rework) `Client._split_kwargs` to `Client._prepare_params`

## [0.7.2] - 2022-03-27

### Bugfix

- fix a bug in registration url

## [0.7.1] - 2022-03-27

### Added

- `Authenticator.from_dict` to instantiate an `Authenticator` from dict and `Authenticator.to_dict` to get authentication data as dict

### Bugfix

- register a new device with `with_username=True` results in a server error due to wrong registration domain

## [0.7.0] - 2021-10-25

### Bugfix

- make sure activation bytes has 8 bytes, otherwise append ‚0‘ in front until 8 bytes are reached
- make sure metadata1 has 8 bytes, otherwise append ‚0‘ in front until 8 bytes are reached
- If installed, use playwright to login with external browser. Please
  [read here](https://playwright.dev/python/docs/intro) how to install playwright.
  Then use `audible.Authenticator.from_login_external(COUNTRY_CODE)` for login.
- fix login issues

## [0.6.0] - 2021-10-21

### Bugfix

- Fix a bug when searching for „resend-approval-link“ in login page

### Changed

- switched to `auth_code_flow` when login (gives an auth code instead of an access token for security purposes)
- `Authenticator.from_login` and `Authenticator.from_login_external` now always register a new device
- `Authenticator` now refreshes `access_token` (when needed) before deregister the device
- now simulate Audible app version 3.56.2 under iOS version 15.0.0
- login process now auto-detect next request method and url

### Misc

- Correct documentation
- Update example download_books_aaxc.py
- Bump httpx to `v0.20.*`

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

- Fetched activation bytes (with `extract=True` argument) will be stored to `activation_bytes` attribute of Authenticator class instance for now. Ignore existing activation bytes and force refresh with `auth.get_activation_bytes(force_refresh=True)`
- `activation_bytes` will be loaded from and save to file. Saved auth files are **not backward compatible** to previous audible versions so keep old files save.
- Add `Client.raw_request` and `AsyncClient.raw_request` method.
- Provide a custom Callback with `approval_callback` keyword argument when login.
- Add classmethod `Authenticator.from_login_external` and method `Authenticator.re_login_external`.
- Add `login_external` function to login.py

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
- The `Authenticator` don’t inherit from MutableMapping anymore
- The `Authenticator` sets allowed instance attributes at creation to `None`, not allowed attributes will raise an Exception
- The `LoginAuthenticator` has been deprecated, use classmethod `Authenticator.from_login` instead.
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
- Uses `httpx` 0.16.\* for now

## [0.4.4] - 2020-10-25

### Bugfix

- Set `padding=„none“` when decrypting license voucher
