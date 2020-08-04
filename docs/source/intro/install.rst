==================
Installation Guide
==================

Requirements / Dependencies
===========================

Audible needs at least *Python 3.6*.

It depends on the following packages:

* beautifulsoup4
* httpx
* pbkdf2
* Pillow
* pyaes
* rsa
* httpcore

Installation
============

The easiest way to install the latest version from PyPI is by using pip::

    pip install audible

You can also use Git to clone the repository from GitHub to install the latest
development version::

    git clone https://github.com/mkb79/audible.git
    cd Audible
    pip install .

Alternatively, install directly from the GitHub repository::

    pip install git+https://github.com/mkb79/audible.git

Command Line Utility
--------------------

The command line utility will be installed as `audible`.

To install just the library on Unix-like operating systems::

    AUDIBLE_INSTALL=lib-only pip install audible

On Windows::

    set AUDIBLE_INSTALL=lib-only
    pip install audible

