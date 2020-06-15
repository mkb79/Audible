============
Marketplaces
============

General Informations
====================

Audible offers his service on 9 different marketplaces. You can read 
more about marketplaces `here <https://audible.custhelp.com/app/answers/detail/a_id/7267/~/what-is-an-audible-marketplace-and-which-is-best-for-me%3F>`_.

.. note::

   Credentials from authentication or device registration are valid 
   for all marketplaces, no matter which country code are used.

.. _country_codes:

Country Codes
=============

This app supports all marketplaces provided by Audible. For every 
marketplace a country code is specified.

.. note::

   When saving credentials the country code will be stored in file. After 
   loading credentials from file this country code will be used by default.

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

The locale argument
===================

You have to provide the country code via the ``locale`` argument.

.. note::

   The locale argument means the same as country code. Because of 
   backward compatibility I don't renamed the locale argument yet. 
   In the future there will be some adjustments. 