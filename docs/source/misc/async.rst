==================
Asynchron requests
==================

By default the AudibleAPI client requests are synchron using the 
requests module.

The client supports now asynchronous request using the httpx module. 
You can instantiate a async client with::

   client = audible.AudibleAPI(..., is_async=True)

Example
=======

.. literalinclude:: ../../../examples/async.py
