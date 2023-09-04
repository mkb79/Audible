==================
Asynchron requests
==================

This app supports asynchronous request using the httpx module.
You can instantiate a async Client with::

   async with audible.AsyncClient(auth=...) as client:
       ...

Example
=======

.. literalinclude:: ../../../examples/async.py
