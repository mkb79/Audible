# Security Policy

`audible` speaks to Amazon's non-public Audible API on your behalf. To do
that it handles authentication material for your Audible/Amazon account:
access and refresh tokens, a device private key, website cookies and
activation bytes. Security is therefore a first-class concern, and reports
are genuinely appreciated.

## Supported versions

Only the **latest release** is supported. Fixes land on `master` and ship
with the next release; there are no back-ports to older versions. The
project is pre-1.0, so the public API may still change between minor
versions.

## Reporting a vulnerability

**Please do not report security issues in public issues, pull requests or
discussions.**

Report privately via GitHub's **[Private Vulnerability
Reporting](https://github.com/mkb79/Audible/security/advisories/new)** (the
"Report a vulnerability" button under the repository's _Security_ tab). If
that is unavailable to you, email `mkb79@hackitall.de` instead.

Please include:

- a description of the issue and its impact,
- the steps or a minimal proof of concept to reproduce it,
- the affected version and your Python version and platform,
- **never** real credentials, tokens, cookies or auth files — redact them,
  or use a synthetic reproduction.

This is a solo, unpaid, spare-time project, so responses are best-effort:
expect an acknowledgement within a couple of weeks. Coordinated disclosure
is appreciated — please allow a reasonable window for a fix before
publishing.

## Scope

**In scope** — issues in this codebase, for example:

- leakage of tokens, cookies, the device private key or activation bytes
  through logs, exception messages, `repr()` output or serialized data,
- weaknesses in the auth-file encryption envelope or its key derivation
  (`audible.aescipher`),
- flaws in the login, device registration or token refresh flows that
  could expose credentials or let them be used unintentionally,
- a crypto or JSON backend behaving differently in a way that weakens any
  of the above.

**Out of scope** — for example:

- using this library against an Audible/Amazon account you do not own, or
  in violation of Audible's terms of service,
- vulnerabilities in third-party dependencies — report those upstream;
  they are tracked here through Dependabot alerts and the `audit` session,
- an unencrypted auth file being readable by someone with access to your
  machine: writing the file without encryption is an explicit choice by
  the calling code (see below),
- issues in Amazon's or Audible's own services.

## A note on stored credentials

`Authenticator.to_file()` can write the auth data either encrypted or as
plain JSON, and **the caller decides**. Passing a password encrypts the
file; `encryption=False` writes the tokens in the clear. If your
application stores credentials, prefer the encrypted form and restrict the
file's permissions.

This is a deliberate part of the API rather than an oversight, so it is not
in itself a vulnerability — but a report showing that the _encrypted_ form
leaks data, or that encryption silently fails, very much is.
