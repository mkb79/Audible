=======
Logging
=======

You can use the Python logging module to log the ouput. You can get the logger
with ``logger = logging.getLogger("audible")``.

I implement a basic log helper, where you can set the basic behavior of logging.
You can use it in this way::

   from audible import log_helper

   # set the log level for the audible package
   log_helper.set_level(LEVEL)

   # console logging
   log_helper.set_console_logger(LEVEL)

   # file logging
   log_helper.set_file_logger(FILENAME, LEVEL)

   # capture warnings
   log_helper.capture_warnings()

The `LEVEL` argument for :meth:`~audible.log_helper.set_console_logger`
and :meth:`~audible.log_helper.set_file_logger` are optional. If a `LEVEL`
is provided, it must be equal or greater than the log level for the package.
Otherwise console or file logger will log nothing.

Following levels are accepted:

- debug
- info
- warning
- error
- critical
- notset

You can use numeric levels too:

- 0 (notset)
- 10 (debug)
- 20 (info)
- 30 (warning)
- 40 (error)
- 50 (critical)
