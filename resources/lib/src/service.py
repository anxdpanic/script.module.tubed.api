# -*- coding: utf-8 -*-
"""
    Copyright (C) 2020 Tubed API (script.module.tubed.api)

    This file is part of script.module.tubed.api

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later.txt for more information.
"""

from .httpd.daemon import HTTPDaemon
from .utils.time import now
from .utils.time import timestamp_diff


def invoke():
    sleep_time = 10
    ping_delay = 60
    ping_timestamp = None

    httpd = HTTPDaemon()

    httpd.clean_cache()

    httpd.start()

    while not httpd.abortRequested():

        if ping_timestamp is None or timestamp_diff(ping_timestamp) >= ping_delay:
            ping_timestamp = str(now())

            if not httpd.ping():
                httpd.restart()

        if httpd.waitForAbort(sleep_time):
            break

    if httpd:
        httpd.shutdown()
