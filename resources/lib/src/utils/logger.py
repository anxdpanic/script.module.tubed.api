# -*- coding: utf-8 -*-
"""
    Copyright (C) 2020 Tubed API (script.module.tubed.api)

    This file is part of script.module.tubed.api

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only.txt for more information.
"""

import logging

try:
    import xbmc
except ImportError:
    xbmc = None


class Log:
    def __init__(self, name='logger.tubed.api', package='', module='', filename=''):
        """
        A simple logger for logging to the Kodi log, Console or a separate Log file
        :param name: Name of the logger
        :type name: str
        :param package: name of the calling package if relevant
        :type package: str
        :param module: name of the calling module if relevant
        :type module: str
        :param filename: filename and path of log file if logging to file is desired
        :type filename: str
        """
        self._package = package
        self._module = module.replace('.pyo', '').replace('.pyc', '').replace('.py', '')

        self._filename = filename
        self._name = name

        if xbmc:
            self._log = xbmc.log
        else:
            self._create_logger()

    def info(self, message):
        """
        Log at `Info` level
        :param message: message to log
        :type message: [str, bytes]
        """
        message = self._decode_message(message)
        if xbmc:
            message = self._format_message(message)
            self._log(message, xbmc.LOGINFO)
        else:
            self._log.info(message)

    def debug(self, message):
        """
        Log at `Debug` level
        :param message: message to log
        :type message: [str, bytes]
        """
        message = self._decode_message(message)
        if xbmc:
            message = self._format_message(message)
            self._log(message, xbmc.LOGDEBUG)
        else:
            self._log.debug(message)

    def warning(self, message):
        """
        Log at `Warning` level
        :param message: message to log
        :type message: [str, bytes]
        """
        message = self._decode_message(message)
        if xbmc:
            message = self._format_message(message)
            self._log(message, xbmc.LOGWARNING)
        else:
            self._log.debug(message)

    def error(self, message):
        """
        Log at `Error` level
        :param message: message to log
        :type message: [str, bytes]
        """
        message = self._decode_message(message)
        if xbmc:
            message = self._format_message(message)
            self._log(message, xbmc.LOGERROR)
        else:
            self._log.error(message)

    def critical(self, message):
        """
        Log at `Critical/Fatal` level
        :param message: message to log
        :type message: [str, bytes]
        """
        message = self._decode_message(message)
        if xbmc:
            message = self._format_message(message)
            self._log(message, xbmc.LOGFATAL)
        else:
            self._log.critical(message)

    @staticmethod
    def _decode_message(message):
        """
        If message is `bytes` decode and return
        :param message: message to decode
        :type message: [str, bytes]
        :return: decoded message
        :rtype: str
        """
        if isinstance(message, bytes):
            message = message.decode('utf-8')

        return message

    def _format_message(self, message):
        """
        Format the log message for Kodi
        :param message: log message to format
        :type message: str
        :return: log message with log leaders added
        :rtype: str
        """
        if self._package and not self._module:
            return '[%s] %s' % (self._package, message)

        if not self._package and self._module:
            return '[%s][%s] %s' % (self._name, self._module, message)

        if self._package and self._module:
            return '[%s][%s] %s' % (self._package, self._module, message)

        return '[%s] %s' % (self._name, message)

    def _create_logger(self):
        """
        Create a python logger
        Creates a file based logger if a filename was provided, otherwise use console based logging
        """
        self._log = logging.getLogger(self._name)

        self._log.setLevel(logging.DEBUG)
        self._log.propagate = False

        formatter = self._get_formatter()

        if not self._filename:
            handler = logging.StreamHandler()

        else:
            handler = logging.handlers.RotatingFileHandler(self._filename,
                                                           encoding='utf-8', mode="w")
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(formatter)
        self._log.addHandler(handler)

    def _get_formatter(self):
        """
        Get formatter for python logging
        :return: formatter for python logging
        :rtype: logging.Formatter
        """
        fmt_lead = '%(asctime)s-[%(levelname)s]'
        fmt_tail = ' %(message)s'
        fmt = '[%(name)s]'

        if self._package and not self._module:
            fmt = '[%s]' % self._package

        elif not self._package and self._module:
            fmt = '[%s][%s]' % ('%(name)s', self._module)

        elif self._package and self._module:
            fmt = '[%s][%s]' % (self._package, self._module)

        return logging.Formatter(fmt.join([fmt_lead, fmt_tail]))
