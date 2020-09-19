# -*- coding: utf-8 -*-
"""
    Copyright (C) 2020 Tubed API (script.module.tubed.api)

    This file is part of script.module.tubed.api

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only.txt for more information.
"""

from copy import deepcopy

from .. import ACCESS_TOKEN
from .. import API_KEY
from .request_handler import v3_request


class Query:
    _base_url = ''

    def __init__(self, method, path, parameters=None, data=None, headers=None):
        if parameters is None:
            parameters = {}

        if data is None:
            data = {}

        if headers is None:
            headers = {}

        self._method = method
        self._url = self._base_url + path.lstrip('/')
        self._parameters = parameters
        self._data = data
        self._headers = headers

    @property
    def url(self):
        return self._url

    @property
    def headers(self):
        return self._headers

    @property
    def data(self):
        return self._data

    @property
    def parameters(self):
        return self._parameters

    @property
    def method(self):
        return self._method

    def __str__(self):
        return '{method}: {url}, {params}, {data}, {headers}' \
            .format(method=self.method.upper(), url=self.url, params=self.parameters,
                    data=self.data, headers=self.headers)

    def invoke(self, func):
        try:
            return func(self.method, self.url, self.parameters, self.data, self.headers)
        except Exception as error:
            raise Exception(str(self)).with_traceback(error.__traceback__)


class V3Query(Query):
    _base_url = 'https://www.googleapis.com/youtube/v3/'

    def __init__(self, method, path, parameters=None, data=None, headers=None):
        if parameters is None:
            parameters = {}
        else:
            parameters = deepcopy(parameters)

        if headers is None:
            headers = {}
        else:
            headers = deepcopy(headers)

        if API_KEY:
            parameters.update({
                'key': API_KEY
            })

        headers.update({
            'Host': 'www.googleapis.com',
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 '
                          '(KHTML, like Gecko) Chrome/39.0.2171.36 Safari/537.36',
            'Accept-Encoding': 'gzip, deflate'
        })

        if ACCESS_TOKEN:
            headers.update({
                'Authorization': 'Bearer {access_token}'.format(access_token=ACCESS_TOKEN)
            })

        super().__init__(method, path, parameters, data, headers)

    def invoke(self, *args, **kwargs):  # pylint: disable=unused-argument
        return super().invoke(v3_request)


def query(obj):
    def wrapper(*args, **kwargs):
        qry = obj(*args, **kwargs)
        return qry.invoke()

    return wrapper
