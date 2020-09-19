# -*- coding: utf-8 -*-
"""
    Copyright (C) 2020 Tubed API (script.module.tubed.api)

    This file is part of script.module.tubed.api

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only.txt for more information.
"""

import socket
from http.server import HTTPServer
from threading import Thread

import requests
import xbmc  # pylint: disable=import-error
import xbmcvfs  # pylint: disable=import-error

from .handler import RequestHandler


class HTTPDaemon(xbmc.Monitor):
    cache_path = xbmcvfs.translatePath('special://temp/script.module.tubed.api')

    def __init__(self):
        self._address = '127.0.0.1'
        self._port = 52520

        self._httpd = None
        self._thread = None

        super().__init__()

    @property
    def address(self):
        return self._address

    @property
    def port(self):
        return int(self._port)

    @property
    def httpd(self):
        return self._httpd

    @httpd.setter
    def httpd(self, value):
        self._httpd = value

    @property
    def thread(self):
        return self._thread

    @thread.setter
    def thread(self, value):
        self._thread = value

    def start(self):
        if not self.httpd:
            self.httpd = self._server()
            self.thread = Thread(target=self.httpd.serve_forever)
            self.thread.daemon = True
            self.thread.start()

    def restart(self):
        self.shutdown()
        self.start()

    def shutdown(self):
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.socket.close()
            self.thread.join()
            self.thread = None
            self.httpd = None

    def ping(self):
        try:
            response = requests.get('http://{address}:{port}/ping'
                                    .format(address=self.address, port=self.port))
            return response.status_code == 204

        finally:
            return False  # pylint: disable=lost-exception

    def clean_cache(self):
        if xbmcvfs.exists(self.cache_path):
            xbmcvfs.rmdir(self.cache_path, force=True)

        return not xbmcvfs.exists(self.cache_path)

    def _server(self):
        try:
            server = HTTPServer((self.address, self.port), RequestHandler)
            return server

        except socket.error:
            return None
