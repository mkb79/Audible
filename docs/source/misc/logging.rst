=======
Logging
=======

In preparation of adding logging in near future I add the 
:class:`~audible._logging.AudibleLogHelper`. You can use it in this way::

   from audible import log_helper

   # set the log level for the audible package
   log_helper.set_level("level")

   # console logging
   log_helper.set_console_logger("level")

   # file logging
   log_helper.set_file_logger("filename", "level")

   # capture warnings
   log_helper.capture_warnings()

The `level` argument for :meth:`~audible.log_helper.set_console_logger` 
and :meth:`~audible.log_helper.set_file_logger` are optional. If a `level` 
is provided, it must be equal or greater as the log level for the package.
Otherwise console or file logger will log nothing.

Following levels are accepted:

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

If you don't want to use the log helper, you can use the python logging module 
on your own purpose. Get the logger with `logging.getLogger("audible")`.

