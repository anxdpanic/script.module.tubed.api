# -*- coding: utf-8 -*-
"""
    Copyright (C) 2020 Tubed API (script.module.tubed.api)

    This file is part of script.module.tubed.api

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later.txt for more information.
"""

import xbmc  # pylint: disable=import-error
import xbmcvfs  # pylint: disable=import-error


class HTTPDaemon(xbmc.Monitor):
    cache_path = xbmcvfs.translatePath('special://temp/script.module.tubed.api')

    def __init__(self):
        pass

    def start(self):
        pass

    def restart(self):
        pass

    def shutdown(self):
        pass

    def ping(self):
        pass

    def clean_cache(self):
        if xbmcvfs.exists(self.cache_path):
            xbmcvfs.rmdir(self.cache_path, force=True)

        return not xbmcvfs.exists(self.cache_path)
