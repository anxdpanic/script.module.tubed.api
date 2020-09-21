# -*- coding: utf-8 -*-
"""
    Copyright (C) 2020 Tubed API (script.module.tubed.api)

    This file is part of script.module.tubed.api

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only.txt for more information.
"""

import json
import time

import requests

from ...utils.json import object_hook
from .. import CLIENT_ID
from .. import CLIENT_SECRET
from ..exceptions import OAuthInvalidGrant
from ..exceptions import OAuthRequestFailed


class Client:
    # https://developers.google.com/youtube/v3/guides/auth/devices
    headers = {
        'Host': 'accounts.google.com',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36',
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    def __init__(self):
        self.client_id = CLIENT_ID
        self.client_secret = CLIENT_SECRET

    def request_codes(self):
        data = {
            'client_id': self.client_id,
            'scope': 'https://www.googleapis.com/auth/youtube'
        }
        response, payload = self._post('https://accounts.google.com/o/oauth2/device/code',
                                       data=data)

        if 'error' in payload:
            payload.update({
                'code': str(response.status_code)
            })
            raise OAuthRequestFailed(payload)

        if response.status_code != requests.codes.ok:  # pylint: disable=no-member
            raise OAuthRequestFailed('Code request failed with status code %s' %
                                     str(response.status_code))

        if response.headers.get('content-type', '').startswith('application/json'):
            return json.loads(json.dumps(payload), object_hook=object_hook)

        raise OAuthRequestFailed('Code request failed with an unknown response')

    def request_access_token(self, code):
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': code,
            'grant_type': 'http://oauth.net/grant_type/device/1.0'
        }

        response, payload = self._post('https://www.googleapis.com/oauth2/v4/token', data=data)

        pending = False

        if 'error' in payload:
            pending = payload['error'] == 'authorization_pending'

            if not pending:
                payload.update({
                    'code': str(response.status_code)
                })
                raise OAuthRequestFailed(payload)

        if (response.status_code != requests.codes.ok) and not pending:  # pylint: disable=no-member
            raise OAuthRequestFailed('Access token request failed with status code %s' %
                                     str(response.status_code))

        if response.headers.get('content-type', '').startswith('application/json'):
            return json.loads(json.dumps(payload), object_hook=object_hook)

        raise OAuthRequestFailed('Access token request failed with an unknown response')

    def refresh_token(self, token):
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'refresh_token': token,
            'grant_type': 'refresh_token'
        }

        response, payload = self._post('https://www.googleapis.com/oauth2/v4/token', data=data)

        if 'error' in payload:
            payload.update({
                'code': str(response.status_code)
            })

            if payload['error'] == 'invalid_grant' and payload['code'] == '400':
                raise OAuthInvalidGrant(payload)

            raise OAuthRequestFailed(payload)

        if response.status_code != requests.codes.ok:  # pylint: disable=no-member
            raise OAuthRequestFailed('Refreshing token failed with status code %s' %
                                     str(response.status_code))

        if response.headers.get('content-type', '').startswith('application/json'):
            return payload['access_token'], time.time() + int(payload.get('expires_in', 3600))

        return '', ''

    def revoke_token(self, token):
        data = {
            'token': token
        }

        response, payload = self._post('https://accounts.google.com/o/oauth2/revoke', data=data)

        if 'error' in payload:
            payload.update({
                'code': str(response.status_code)
            })
            raise OAuthRequestFailed(payload)

        if response.status_code != requests.codes.ok:  # pylint: disable=no-member
            raise OAuthRequestFailed('Token revocation failed')

    def _post(self, url, data):
        response = requests.post(url, data=data, headers=self.headers)

        response.encoding = 'utf-8'

        try:
            return response, response.json()
        except ValueError:
            return response, {}
