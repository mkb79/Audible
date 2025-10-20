================================
Audible |version| documentation!
================================

.. image:: https://img.shields.io/pypi/v/audible.svg
   :target: https://pypi.org/project/audible/
   :alt: PyPI Version

.. image:: https://img.shields.io/pypi/l/audible.svg
   :target: https://pypi.org/project/audible
   :alt: License

.. image:: https://img.shields.io/pypi/pyversions/audible.svg
   :target: https://pypi.org/project/audible
   :alt: Python Versions

.. image:: https://img.shields.io/pypi/status/audible.svg
   :target: https://pypi.org/project/audible
   :alt: Status

.. image:: https://img.shields.io/pypi/wheel/audible.svg
   :target: https://pypi.org/project/audible
   :alt: Wheel

.. image:: https://github.com/mkb79/audible/workflows/Tests/badge.svg
   :target: https://github.com/mkb79/audible/actions?workflow=Tests
   :alt: Tests

.. image:: https://codecov.io/gh/mkb79/audible/branch/master/graph/badge.svg
   :target: https://codecov.io/gh/mkb79/audible
   :alt: Codecov

.. image:: https://www.codefactor.io/repository/github/mkb79/audible/badge
   :target: https://www.codefactor.io/repository/github/mkb79/audible
   :alt: CodeFactor

.. image:: https://img.shields.io/pypi/dm/audible.svg
   :target: https://pypi.org/project/audible
   :alt: Downloads

-------------------

**Audible** is a Python low-level interface to communicate with the non-publicly
`Audible <https://en.m.wikipedia.org/wiki/Audible_(service)>`_ API.
It enables Python developers to create their own Audible services.

**Quick Example** - Get your audiobook library in 3 lines::

    import audible

    auth = audible.Authenticator.from_file("audible-auth.json")
    with audible.Client(auth=auth) as client:
        library = client.get("1.0/library", num_results=999)

**Key Features:**

✓ **Sync & Async** - Both synchronous and asynchronous API clients

✓ **Full API Coverage** - Access to all Audible API endpoints

✓ **Type Safe** - Complete type hints for better IDE support

✓ **Multi-Marketplace** - Support for all Audible marketplaces (US, UK, DE, FR, etc.)

✓ **Easy Authentication** - Multiple authentication methods including external browser

**Installation**::

    pip install audible

.. tip::
   **New to Audible?** Start with the :doc:`intro/quickstart` guide for a
   step-by-step introduction in just 5 minutes!

.. note::
   **Need quick help?** Check out our new :doc:`help/faq` for answers to common questions!

**What's New:**

✨ **Enhanced Documentation** - Restructured for better navigation with skill-level indicators

📚 **New FAQ Section** - Comprehensive answers to common questions

🎯 **Improved Examples** - More practical code examples and use cases

🔧 **Better Organization** - Clearer separation between beginner and advanced topics

.. note::

   For a command-line interface, check out
   `audible-cli <https://github.com/mkb79/audible-cli>`_ which supports:

   - Downloading audiobooks (aax/aaxc), cover, PDF and chapter files
   - Exporting library to CSV
   - Getting activation bytes
   - Custom plugin commands

|

.. toctree::
   :maxdepth: 2
   :caption: 🚀 Getting Started

   intro/install
   intro/quickstart
   intro/understanding

.. toctree::
   :maxdepth: 2
   :caption: 🔐 Authentication

   auth/authorization
   auth/authentication
   auth/register

.. toctree::
   :maxdepth: 2
   :caption: 📚 Core Features

   core/async
   core/load_save
   marketplaces/marketplaces

.. toctree::
   :maxdepth: 2
   :caption: 🚀 Advanced Topics

   advanced/client_api
   advanced/logging

.. toctree::
   :maxdepth: 2
   :caption: 💡 Examples & Recipes

   help/examples
   help/external_api

.. toctree::
   :maxdepth: 2
   :caption: 📖 API Reference

   modules/audible

.. toctree::
   :maxdepth: 2
   :caption: ❓ Help & Resources

   help/faq
   help/troubleshooting
   help/changelog


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
