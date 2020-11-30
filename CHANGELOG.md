# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## Unreleased

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

## [0.4.4] - 2020-10-25

### Bugfix

- Set `padding="none"` when decrypting license voucher 
