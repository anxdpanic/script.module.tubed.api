# -*- coding: utf-8 -*-
"""
    Copyright (C) 2020 Tubed API (script.module.tubed.api)

    This file is part of script.module.tubed.api

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only.txt for more information.
"""

from ..query import V3Query
from ..query import query


# https://developers.google.com/youtube/v3/docs/watermarks/set
@query
def upload(parameters=None, data=None):
    return V3Query('post', 'watermarks/set', parameters=parameters, data=data)


# https://developers.google.com/youtube/v3/docs/watermarks/unset
@query
def delete(parameters=None):
    return V3Query('post', 'watermarks/unset', parameters=parameters)
