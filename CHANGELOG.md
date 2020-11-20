# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## Unreleased

### Added

- Added a guide to use authentication with [Postman](https://www.postman.com).
- Added support to output the whole activation bytes with `get_activation_bytes(extract=False, ...)`.
- Added support to install Sphinx documentation dependencies with `pip install audible[docs]`.
- Added support to fetch website cookies for another country with `Authenticator.set_website_cookies_for_country`.
- Added `Client.put` and `AsyncClient.put`.
- Added support to solve approval alerts during login
- Added `.readthedocs.yml` config file

### Changed

- The `FileAuthenticator` has been deprecated, use classmethod `Authenticator.from_file` instead.
- The `LoginAuthenticator` has been deprecated, use  classmethod `Authenticator.from_login` instead.
- Changed metadata encryption and decryption internal code base and moved them to `metadata.py`. ([#]())
- Rework documentation.

### Remove

- deprecated `AudibleAPI`

## [0.4.4] - 2020-10-25

### Bugfix

- Set `padding="none"` when decrypting license voucher 
