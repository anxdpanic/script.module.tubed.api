# -*- coding: utf-8 -*-
"""
    Copyright (C) 2020 Tubed API (script.module.tubed.api)

    This file is part of script.module.tubed.api

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later.txt for more information.
"""

from ..query import V3Query
from ..query import query


# https://developers.google.com/youtube/v3/docs/channelBanners/insert
@query
def insert(parameters=None):
    return V3Query('post', 'channelBanners', parameters=parameters)
