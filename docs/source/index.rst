================================
Audible |version| documentation!
================================

.. image:: https://img.shields.io/pypi/v/audible.svg
   :target: https://pypi.org/project/audible/

.. image:: https://img.shields.io/pypi/l/audible.svg
   :target: https://pypi.org/project/audible

.. image:: https://img.shields.io/pypi/pyversions/audible.svg
   :target: https://pypi.org/project/audible

.. image:: https://img.shields.io/pypi/status/audible.svg
   :target: https://pypi.org/project/audible

.. image:: https://img.shields.io/pypi/wheel/audible.svg
   :target: https://pypi.org/project/audible

.. image:: https://img.shields.io/travis/mkb79/audible/master.svg?logo=travis
   :target: https://travis-ci.org/mkb79/audible

.. image:: https://www.codefactor.io/repository/github/mkb79/audible/badge
   :target: https://www.codefactor.io/repository/github/mkb79/audible

.. image:: https://img.shields.io/pypi/dm/audible.svg
   :target: https://pypi.org/project/audible

-------------------

**Audible** is a Python low-level interface to communicate with the non-publicly 
`Audible <https://en.m.wikipedia.org/wiki/Audible_(service)>`_ API.
It enables Python developers to create there own Audible services. Asynchronous 
communication with the Audible API is supported.

.. note::

   For a basic command line interface take a look at my
   `audible-cli <https://github.com/mkb79/audible-cli>`_ package.
   This package supports:

   - downloading audiobooks (aax/aaxc), cover, PDF and chapter file
   - export library to `csv <https://en.wikipedia.org/wiki/Comma-separated_values>`_
     files
   - get activation bytes
   - add own plugin commands

|

.. toctree::
   :maxdepth: 1
   :caption: Table of Contents

   intro/install
   intro/getting_started
   marketplaces/marketplaces
   auth/authorization
   auth/authentication
   auth/register
   misc/load_save
   misc/async
   misc/advanced
   misc/logging
   misc/external_api
   misc/examples
   modules/audible


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
