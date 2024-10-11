============
Marketplaces
============

General Information
===================

Audible offers his service on 11 different marketplaces. You can read more about
marketplaces
`here <https://help.audible.com/s/article/what-is-an-audible-marketplace-and-which-is-best-for-me?language=en_US>`_.

.. note::

   Except website cookies, authentication data from device registration are valid
   for all marketplaces, no matter which marketplace are used.

.. note::

   The Brazilian marketplace was added in mid-2023.

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
   * - Audible.com.au
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
   * - Audible.com.br
     - Brazil
     - br

The locale argument
===================

The locale argument have the same meaning as the country code argument. Because
of backward compatibility I didn't renamed the locale argument yet. So if you
are asked for a `locale` than provide a country code from above.

.. note::

   The country code for the Brazilian marketplace needs Audible > 0.8.2.
   How to use these marketplace with a previous version read
   `this comment <https://github.com/mkb79/Audible/issues/194#issuecomment-1728896926>`_.
