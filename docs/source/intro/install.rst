==================
Installation Guide
==================

.. raw:: html

   <div class="skill-level-container">
       <span class="skill-level-badge skill-level-beginner">Beginner</span>
       <span class="reading-time-badge">3 min read</span>
   </div>

Requirements / Dependencies
===========================

Audible needs at least *Python 3.10*.

It depends on the following packages:

* beautifulsoup4
* httpx
* pbkdf2
* Pillow
* pyaes
* rsa

Installation
============

The easiest way to install the latest version from PyPI is by using pip::

    pip install audible

You can also use Git to clone the repository from GitHub to install the latest
development version::

    git clone https://github.com/mkb79/audible.git
    cd Audible
    pip install .

Alternatively, install it directly from the GitHub repository::

    pip install git+https://github.com/mkb79/audible.git
