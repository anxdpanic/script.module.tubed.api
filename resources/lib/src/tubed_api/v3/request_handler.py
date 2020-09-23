# -*- coding: utf-8 -*-
"""
    Copyright (C) 2020 Tubed API (script.module.tubed.api)

    This file is part of script.module.tubed.api

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only.txt for more information.
"""

import json

from requests import Session
from requests.adapters import HTTPAdapter

from ..utils.json import object_hook


def _status_response(response):
    if 200 <= response.status_code < 300:
        payload = {
            'error': {
                'message': 'v3 Data API request was successful',
                'errors': [{
                    'reason': 'v3RequestSucceeded'
                }],
                'code': response.status_code
            }
        }

    else:
        payload = {
            'error': {
                'message': 'v3 Data API request failed',
                'errors': [{
                    'reason': 'v3RequestFailed'
                }],
                'code': response.status_code
            }
        }

    return json.loads(json.dumps(payload), object_hook=object_hook)


def v3_request(method, url, parameters, data, headers):
    adapter = HTTPAdapter(max_retries=3)
    session = Session()

    session.mount('http://', adapter)
    session.mount('https://', adapter)

    response = getattr(session, method)(url, params=parameters, data=data,
                                        headers=headers, timeout=(2, 60))

    response.encoding = 'utf-8'

    try:
        return response.json(object_hook=object_hook)
    except ValueError:
        return _status_response(response)
