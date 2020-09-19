# -*- coding: utf-8 -*-
"""
    Copyright (C) 2020 Tubed API (script.module.tubed.api)

    This file is part of script.module.tubed.api

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later.txt for more information.
"""

import json

from .quality import Quality
from .video_info import VideoInfo
from ...utils.json import object_hook


def resolve(video_id, quality=None, language='en-US', region='US'):
    if not quality:
        quality = Quality('mp4')

    video_info = VideoInfo(language, region)
    video = video_info.get_video(video_id, quality)

    return json.loads(json.dumps(video), object_hook=object_hook)
