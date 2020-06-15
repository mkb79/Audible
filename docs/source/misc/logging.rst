=======
Logging
=======

In preparation of adding logging in near future I add following functions::

   import audible

   # console logging
   audible.set_console_logger("level")

   # file logging
   audible.set_file_logger("filename", "level")

Following levels will be accepted:

- debug
- info
- warning
- error
- critical

You can use numeric levels too:

- 10 (debug)
- 20 (info)
- 30 (warning)
- 40 (error)
- 50 (critical)