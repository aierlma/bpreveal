# Copyright 2015 The TensorFlow Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
# Modifications made by Charles McAnany
# - Converted names to camelCase,
# - Changed setVerbosity to take a string and not an int.
# - Removed some functions I don't need.
# - Renamed warn -> warning and fatal -> critical. These are the names used in
#   the Python Standard Library

"""Logging utilities, taken from Tensorflow.

``logUtils`` is meant to be a drop-in replacement for the standard library logging module.
If you're feeling lazy, you can even ``from bpreveal import logUtils as logging``.
"""
import logging as _logging
import sys as _sys
import _thread
import typing
import tqdm
import traceback as _traceback
from logging import DEBUG
from logging import ERROR
from logging import CRITICAL
from logging import INFO
from logging import WARNING
import threading

# Don't use this directly. Use get_logger() instead.
_LOGGER = None
_LOGGER_LOCK = threading.Lock()


def _getCaller(offset=3):
    """Returns a code and frame object for the lowest non-logging stack frame."""
    # Use sys._getframe().  This avoids creating a traceback object.
    # pylint: disable=protected-access
    f = _sys._getframe(offset)
    # pylint: enable=protected-access
    ourFile = f.f_code.co_filename
    f = f.f_back
    while f:
        code = f.f_code
        if code.co_filename != ourFile:
            return code, f
        f = f.f_back
    return None, None


def _loggerFindCaller(stackInfo=False, stacklevel=1):
    del stacklevel
    code, frame = _getCaller(4)
    sinfo = None
    if stackInfo:
        sinfo = '\n'.join(_traceback.format_stack())
    if code:
        return (code.co_filename, frame.f_lineno, code.co_name, sinfo)
    return '(unknown file)', 0, '(unknown function)', sinfo


def getLogger() -> _logging.Logger:
    """Return TF logger instance.

    :return: An instance of the Python logging library Logger.

    See Python documentation (https://docs.python.org/3/library/logging.html)
    for detailed API. Below is only a summary.

    The logger has 5 levels of logging from the most serious to the least:

    1. CRITICAL
    2. ERROR
    3. WARNING
    4. INFO
    5. DEBUG

    The logger has the following methods, based on these logging levels:

    1. ``critical(msg, *args, **kwargs)``
    2. ``error(msg, *args, **kwargs)``
    3. ``warning(msg, *args, **kwargs)``
    4. ``info(msg, *args, **kwargs)``
    5. ``debug(msg, *args, **kwargs)``

    The `msg` can contain string formatting.  An example of logging at the `ERROR`
    level
    using string formatting is:

    >>> logUtils.getLogger().error("The value %d is invalid.", 3)

    You can also specify the logging verbosity.  In this case, the
    WARNING level log will not be emitted:

    >>> logUtils.setVerbosity("ERROR")
    >>> logUtils.getLogger().warning("This is a warning.")
    """
    global _LOGGER

    # Use double-checked locking to avoid taking lock unnecessarily.
    if _LOGGER:
        return _LOGGER

    _LOGGER_LOCK.acquire()

    try:
        if _LOGGER:
            return _LOGGER

        # Scope the TensorFlow logger to not conflict with users' loggers.
        logger = _logging.getLogger('BPReveal')

        # Override findCaller on the logger to skip internal helper functions
        logger.findCaller = _loggerFindCaller

        # Don't further configure the TensorFlow logger if the root logger is
        # already configured. This prevents double logging in those cases.
        if not _logging.getLogger().handlers:
            # Determine whether we are in an interactive environment
            _interactive = False
            try:
                # This is only defined in interactive shells.
                if _sys.ps1:
                    _interactive = True
            except AttributeError:
                # Even now, we may be in an interactive shell with `python -i`.
                _interactive = _sys.flags.interactive

            # If we are in an interactive environment (like Jupyter), set loglevel
            # to INFO and pipe the output to stdout.
            if _interactive:
                logger.setLevel(INFO)
                _loggingTarget = _sys.stdout
            else:
                _loggingTarget = _sys.stderr

            # Add the output handler.
            loggingFormat = _logging.Formatter('%(levelname)s : %(asctime)s :'
                                               '%(filename)s:%(lineno)d : %(message)s',
                                               datefmt='%Y-%m-%d %H:%M:%S')
            _handler = _logging.StreamHandler(_loggingTarget)
            _handler.setFormatter(loggingFormat)
            logger.addHandler(_handler)

        _LOGGER = logger
        return _LOGGER

    finally:
        _LOGGER_LOCK.release()


def log(level: int | str, msg: str, *args, **kwargs):
    """Log message at the given level."""
    if isinstance(level, str):
        level = _LEVEL_MAP[level]
    getLogger().log(level, msg, *args, **kwargs)


def debug(msg: str, *args, **kwargs):
    """For nitty-gritty details."""
    getLogger().debug(msg, *args, **kwargs)


def error(msg: str, *args, **kwargs):
    """Something went horribly wrong."""
    getLogger().error(msg, *args, **kwargs)


def critical(msg: str, *args, **kwargs):
    """The world is ending. This is not used by BPReveal."""
    getLogger().critical(msg, *args, **kwargs)


def info(msg: str, *args, **kwargs):
    """Normal progress messages."""
    getLogger().info(msg, *args, **kwargs)


def warning(msg: str, *args, **kwargs):
    """Something the user should pay attention to."""
    getLogger().warning(msg, *args, **kwargs)


_LEVEL_NAMES = {
    CRITICAL: 'CRITICAL',
    ERROR: 'ERROR',
    WARNING: 'WARNING',
    INFO: 'INFO',
    DEBUG: 'DEBUG',
}

_LEVEL_MAP = {"CRITICAL": _logging.CRITICAL,
              "ERROR": _logging.ERROR,
              "WARNING": _logging.WARNING,
              "INFO": _logging.INFO,
              "DEBUG": _logging.DEBUG}

# Mask to convert integer thread ids to unsigned quantities for logging
# purposes
_THREAD_ID_MASK = 2 * _sys.maxsize + 1

# Counter to keep track of number of log entries per token.
_log_counter_per_token = {}


def logFirstN(level, msg, n, *args):
    """Log 'msg % args' at level 'level' only first 'n' times.

    Not threadsafe.

    :param level: The level at which to log.
    :param msg: The message to be logged.
    :param n: The number of times this should be called before it is logged.
    :param args: The args to be substituted into the msg.
    """
    token = msg % args
    global _log_counter_per_token  # pylint: disable=global-variable-not-assigned
    _log_counter_per_token[token] = 1 + _log_counter_per_token.get(token, -1)
    count = _log_counter_per_token[token]
    logIf(level, msg, count < n, *args)


def logIf(level: str | int, msg: str, condition: bool, *args):
    """Log 'msg % args' at level 'level' only if condition is fulfilled."""
    if condition:
        log(level, msg, *args)


def _getFileAndLine():
    """Returns (filename, linenumber) for the stack frame."""
    code, f = _getCaller()
    if not code:
        return ('<unknown>', 0)
    return (code.co_filename, f.f_lineno)


def getVerbosity() -> int:
    """Return how much logging output will be produced."""
    return getLogger().getEffectiveLevel()


def setVerbosity(userLevel: str | int):
    """Set the verbosity for this BPReveal session.

    BPReveal uses the python logging module for its printing, and
    less-important information is logged at lower levels.
    Level options are CRITICAL, ERROR, WARNING, INFO, and DEBUG.

    :param userLevel: The level of logging that you'd like to enable.
        It may be an actual logging level (like ``logUtils.ERROR``), or
        a string naming one of the logging levels (like ``"ERROR"``).
    """
    if isinstance(userLevel, str):
        level = _LEVEL_MAP[userLevel]
    else:
        level = userLevel
    getLogger().setLevel(level)
    debug("Logging configured.")


def _getThreadId():
    """Get id of current thread, suitable for logging as an unsigned quantity."""
    threadId = _thread.get_ident()
    return threadId & _THREAD_ID_MASK


def wrapTqdm(iterable: typing.Iterable | int, logLevel: str | int = _logging.INFO,
             **tqdmKwargs) -> tqdm.tqdm:
    """Create a tqdm logger or a dummy, based on current logging level.

    :param iterable: The thing to be wrapped, or the number to be counted to.
    :param logLevel: The log level at which you'd like the tqdm to print progress.
    :param tqdmKwargs: Additional keyword arguments passed to tqdm.
    :return: Either a tqdm that will do logging, or an iterable that won't log.
    :rtype: A tqdm-like object supporting either iteration or ``.update()``.

    Sometimes, you want to display a tqdm progress bar only if the logging level is
    high. Call this with something you want to iterate over OR an integer giving the
    total number of things that will be processed (corresponding to::

        pbar = tqdm.tqdm(total=10000)
        while condition:
            pbar.update()
        )

    If iterable is an integer, then this will return a tqdm that you need to
    call update() on, otherwise it'll return something you can use as a loop iterable.

    logLevel may either be a level from the logging module (like logging.INFO) or a
    string naming the log level (like "info")
    """
    if isinstance(logLevel, str):
        # We were given a string, so convert that to a logging level.
        logLevelInternal: int = _LEVEL_MAP[logLevel.upper()]
    elif isinstance(logLevel, int):
        logLevelInternal: int = logLevel
    else:
        assert False, "Invalid type passed to wrapTqdm"

    if isinstance(iterable, int):
        if getLogger().isEnabledFor(logLevelInternal):
            return tqdm.tqdm(total=iterable, **tqdmKwargs)
        return tqdm.tqdm(total=iterable, **tqdmKwargs, disable=True)
    if isinstance(iterable, typing.Iterable):
        iterableOut: typing.Iterable = iterable
        if getLogger().isEnabledFor(logLevelInternal):
            return tqdm.tqdm(iterableOut, **tqdmKwargs)
        return tqdm.tqdm(iterableOut, **tqdmKwargs, disable=True)
    assert False, "Your iterable is not valid with tqdm."
