==================
Asynchron requests
==================

By default the AudibleAPI client requests are synchron using the 
requests module.

This app supports now asynchronous request using the httpx module. 
You can instantiate a async client with::

   client = audible.AsyncClient(...)

Example
=======

.. literalinclude:: ../../../examples/async.py
