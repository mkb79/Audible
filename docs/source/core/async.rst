==================
Asynchron requests
==================

.. raw:: html

   <div class="skill-level-container">
       <span class="skill-level-badge skill-level-intermediate">Intermediate</span>
       <span class="reading-time-badge">8 min read</span>
   </div>

This app supports asynchronous request using the httpx module.
You can instantiate a async Client with::

   async with audible.AsyncClient(auth=...) as client:
       ...

Example
=======

.. literalinclude:: ../../../examples/async.py
