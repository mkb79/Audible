============
Marketplaces
============

General Information
===================

Audible offers his service on 10 different marketplaces. You can read more about
marketplaces
`here <https://help.audible.com/s/article/what-is-an-audible-marketplace-and-which-is-best-for-me?language=en_US>`_.

.. note::

   Except website cookies, authentication data from device registration are valid
   for all marketplaces, no matter which marketplace are used.

.. _country_codes:

Country Codes
=============

This app supports all marketplaces provided by Audible. For every marketplace a
country code is associated.

.. note::

   The country code of the selected marketplace is stored to file, when you
   save your authentication data. So, after loading this data from file, the
   stored country code is used by default.

.. list-table:: Marketplaces with country codes
   :widths: 20 50 15
   :header-rows: 1

   * - Marketplace
     - Supported Countries
     - Country Code
   * - Audible.com
     - US and all other countries not listed
     - us
   * - Audible.ca
     - Canada
     - ca
   * - Audible.co.uk
     - UK and Ireland
     - uk
   * - Audible.co.au
     - Australia and New Zealand
     - au
   * - Audible.fr
     - France, Belgium, Switzerland
     - fr
   * - Audible.de
     - Germany, Austria, Switzerland
     - de
   * - Audible.co.jp
     - Japan
     - jp
   * - Audible.it
     - Italy
     - it
   * - Audible.co.in
     - India
     - in
   * - Audible.es
     - Spain
     - es

The locale argument
===================

The locale argument have the same meaning as the country code argument. Because
of backward compatibility I didn't renamed the locale argument yet. So if you
are asked for a `locale` than provide a country code from above.
