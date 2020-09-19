# -*- coding: utf-8 -*-
"""
    Copyright (C) 2020 Tubed API (script.module.tubed.api)

    This file is part of script.module.tubed.api

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later.txt for more information.
"""


class ManifestGenerator:

    def __init__(self, cipher):
        self._cipher = cipher

    @property
    def cipher(self):
        return self._cipher

    def generate(self, video_id, formats, duration):
        _ = video_id
        _ = formats
        _ = duration
        _ = self._cipher
        return None, None
