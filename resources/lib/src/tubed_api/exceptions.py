# -*- coding: utf-8 -*-
"""
    Copyright (C) 2020 Tubed API (script.module.tubed.api)

    This file is part of script.module.tubed.api

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only.txt for more information.
"""


class TubedAPIException(Exception):
    _message = ''

    def __init__(self, message=''):
        super().__init__()
        if message:
            self._message = message

    @property
    def message(self):
        return self._message


class TubedOAuthException(TubedAPIException):
    pass


class ResourceUnavailable(TubedAPIException):
    pass


class CipherNotFound(TubedAPIException):
    pass


class CipherUnknownMethod(TubedAPIException):
    pass


class CipherFailedDecipher(TubedAPIException):
    pass


class ContentRestricted(TubedAPIException):
    pass


class OAuthRequestFailed(TubedOAuthException):
    pass


class OAuthInvalidGrant(TubedOAuthException):
    pass
