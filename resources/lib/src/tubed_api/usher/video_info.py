# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2020 plugin.video.youtube
    Copyright (C) 2020 Tubed API (script.module.tubed.api)

    This file is part of script.module.tubed.api

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only.txt for more information.
"""

import json
import random
import re
from copy import deepcopy
from urllib.parse import parse_qsl
from urllib.parse import quote

import requests
import xbmcvfs  # pylint: disable=import-error

from .. import ACCESS_TOKEN
from .cipher import Cipher
from .mpeg_dash import ManifestGenerator
from .subtitles import Subtitles


class VideoInfo:
    _headers = {
        'Host': 'www.youtube.com',
        'Connection': 'keep-alive',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/53.0.2785.143 Safari/537.36',
        'Accept': '*/*',
        'DNT': '1',
        'Referer': 'https://www.youtube.com',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'en-US,en;q=0.8,de;q=0.6'
    }

    def __init__(self, language='en-US', region='US'):
        self._access_token = ACCESS_TOKEN
        self._language = language
        self._region = region
        self._itags = {}

    @property
    def language(self):
        return self._language

    @property
    def region(self):
        return self._region

    @property
    def headers(self):
        return deepcopy(self._headers)

    @property
    def itags(self):
        if not self._itags:
            self._load_itags()
        return self._itags

    def _load_itags(self):
        with xbmcvfs.File('itags.json') as itag_file:
            self._itags = json.load(itag_file)

    def get_watch_page(self, video_id):
        params = {
            'v': video_id,
            'hl': self.language,
            'gl': self.region
        }

        if self._access_token:
            params['access_token'] = self._access_token

        result = requests.get('https://www.youtube.com/watch', params=params,
                              headers=self.headers, allow_redirects=True)
        return {
            'html': result.text,
            'cookies': result.cookies
        }

    def get_embed_page(self, video_id):
        params = {
            'hl': self.language,
            'gl': self.region
        }

        if self._access_token:
            params['access_token'] = self._access_token

        url = 'https://www.youtube.com/embed/{video_id}'.format(video_id=video_id)

        result = requests.get(url, params=params, headers=self.headers, allow_redirects=True)
        return {
            'html': result.text,
            'cookies': result.cookies
        }

    @staticmethod
    def generate_cpn():
        # https://github.com/rg3/youtube-dl/blob/master/youtube_dl/extractor/youtube.py#L1381
        # LICENSE: The Unlicense
        # cpn generation algorithm is reverse engineered from base.js.
        # In fact it works even with dummy cpn.
        cpn_alphabet = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_'
        cpn = ''.join((cpn_alphabet[random.randint(0, 256) & 63] for _ in range(0, 16)))
        return cpn

    @staticmethod
    def get_player_config(html):
        config = {}
        lead = 'ytplayer.config = '
        tails = [
            'ytplayer.load',
            'ytplayer.web_player_context_config'
        ]

        for tail in tails:
            pos = html.find(lead)
            if pos >= 0:
                html2 = html[pos + len(lead):]
                pos = html2.find(tail)
                if pos >= 0:
                    config = html2[:pos].rstrip().rstrip(';').rstrip()
                    try:
                        config = json.loads(config)
                        break

                    except (TypeError, ValueError):
                        config = {}

        try:
            result = re.search(r'var blankSwfConfig\s*=\s*(?P<player_config>{.+?})'
                               r';\s*var fillerData', html)
            player_config = json.loads(result.group('player_config'))

        except:  # pylint: disable=bare-except
            player_config = {}

        player_config.update(config)

        if 'args' not in player_config:
            player_config['args'] = {}

        try:
            player_response = player_config['args'].get('player_response', {})
            player_response = json.loads(player_response)

        except:  # pylint: disable=bare-except
            player_response = {}

        try:
            result = re.search(r'window\["ytInitialPlayerResponse"]\s*=\s*\(\s*'
                               r'(?P<player_response>{.+?})\s*\);', html)
            player_config['args']['player_response'] = json.loads(result.group('player_response'))
        except TypeError:
            player_config['args']['player_response'] = {}

        player_config['args']['player_response'].update(player_response)

        return player_config

    @staticmethod
    def _curl_headers(cookies):
        if not cookies:
            return ''

        cookies_list = []
        for cookie in cookies:
            cookies_list.append('{0}={1};'.format(cookie.name, cookie.value))

        if cookies_list:
            return 'Cookie={cookies}'.format(cookies=quote(''.join(cookies_list)))

        return ''

    @staticmethod
    def image_map():
        return [
            {
                'from': 'iurlhq',
                'to': 'high',
                'image': 'hqdefault.jpg'
            },
            {
                'from': 'iurlmq',
                'to': 'medium',
                'image': 'mqdefault.jpg'
            },
            {
                'from': 'iurlsd',
                'to': 'standard',
                'image': 'sddefault.jpg'
            },
            {
                'from': 'thumbnail_url',
                'to': 'default',
                'image': 'default.jpg'
            }
        ]

    @staticmethod
    def playability(status):
        if ((status.get('fallback', True) and status.get('status', 'ok').lower() == 'ok') or
                status.get('desktopLegacyAgeGateReason', 1) == 1):
            return {
                'playable': True,
                'reason': ''
            }

        if status.get('status') == 'LIVE_STREAM_OFFLINE':
            reason = status.get('reason')
            if not reason:
                streamability = status.get('liveStreamability', {})
                renderer = streamability.get('liveStreamabilityRenderer', {})
                slate = renderer.get('offlineSlate', {})
                offline_slate_renderer = slate.get('liveStreamOfflineSlateRenderer', {})
                main_text = offline_slate_renderer.get('mainText', {})
                text_runs = main_text.get('runs', [{}])

                reason_text = []
                for text in text_runs:
                    reason_text.append(text.get('text', ''))

                if reason_text:
                    reason = ''.join(reason_text)
        else:
            reason = status.get('reason')

            if 'errorScreen' in status and 'playerErrorMessageRenderer' in status['errorScreen']:
                renderer = status['errorScreen']['playerErrorMessageRenderer']

                descript_reason = renderer.get('subreason', {}).get('simpleText')
                general_reason = renderer.get('reason', {}).get('simpleText')

                if descript_reason:
                    reason = descript_reason
                elif general_reason:
                    reason = general_reason

        if not reason:
            reason = 'UNKNOWN'

        try:
            reason = reason.encode('raw_unicode_escape').decode('utf-8')
        except:  # pylint: disable=bare-except
            pass

        return {
            'playable': False,
            'reason': reason
        }

    @staticmethod
    def requires_cipher(formats):
        flist = []

        if len(formats) > 0:
            try:
                flist = formats[0].get('signatureCipher', formats[0].get('cipher')).split(',')
            except AttributeError:
                flist = formats[0].get('url', '').split('&')

        return (len(flist) > 0) and ('s' in dict(parse_qsl(flist[0])))

    def get_player_javascript(self, video_id, javascript_url=''):
        def _normalize(url):
            if url in ['http://', 'https://']:
                url = ''

            if url and not url.startswith('http'):
                url = 'https://www.youtube.com/%s' % \
                      url.lstrip('/').replace('www.youtube.com/', '')

            return url

        if javascript_url:
            return _normalize(javascript_url)

        page_result = self.get_embed_page(video_id)
        html = page_result.get('html')

        if not html:
            return ''

        _player_config = '{}'
        player_config = dict()

        def _find_config(lead, tail):
            if html.find(tail) == -1:
                tail = '});'

            pos = html.find(lead)

            if pos >= 0:
                html2 = html[pos + len(lead):]
                pos = html2.find(tail)

                if pos >= 0:
                    return html2[:pos]

            return None

        _player_config = \
            _find_config('yt.setConfig({\'PLAYER_CONFIG\': ', ',\'EXPERIMENT_FLAGS\':')

        if _player_config is None:
            _player_config = \
                _find_config(',\'PLAYER_CONFIG\': ', 'yt.setConfig({INNERTUBE_API_VERSION:')

        if _player_config is None:
            _player_config = '{}'

        try:
            player_config.update(json.loads(_player_config))
        except TypeError:
            pass
        finally:
            javascript_url = player_config.get('assets', {}).get('js', '')

        return _normalize(javascript_url)

    @staticmethod
    def _decipher_signature(cipher, url):
        if not re.search('/s/[0-9A-F.]+', url) or re.search('/signature/[0-9A-F.]+', url):
            return url

        if not cipher:
            raise Exception('Cipher not found')

        signature_param = 'signature'
        match = re.search('/sp/(?P<signature_param>[^/]+)', url)
        if match:
            signature_param = match.group('signature_param')

        match = re.search('/s/(?P<signature>[0-9A-F.]+)', url)
        if match:
            signature = cipher.signature(match.group('signature'))
            url = re.sub(
                '/s/[0-9A-F.]+',
                ''.join(['/', signature_param, '/', signature]),
                url
            )
            return url

        return ''

    def _get_video_info(self, video_id):  # pylint: disable=too-many-locals, too-many-branches, too-many-statements
        headers = self.headers
        if self._access_token:
            headers['Authorization'] = 'Bearer %s' % self._access_token

        params = {
            'hl': self.language,
            'gl': self.region,
            'ssl_stream': '1',
            'html5': '1'
        }

        page_result = self.get_watch_page(video_id)
        html = page_result.get('html')
        cookies = page_result.get('cookies')

        player_config = self.get_player_config(html)
        curl_headers = self._curl_headers(cookies)

        if not cookies:
            cookies = {}

        player_args = player_config.get('args', {})
        player_response = player_args.get('player_response', {})
        playability_status = player_response.get('playabilityStatus', {})

        params['video_id'] = video_id
        params['eurl'] = ''.join(['https://youtube.googleapis.com/v/', video_id])
        params['sts'] = player_config.get('sts', '')
        params['t'] = player_args.get('t', '')
        params['c'] = player_args.get('c', 'WEB')
        params['cver'] = player_args.get('cver', '1.20170712')
        params['cplayer'] = player_args.get('cplayer', 'UNIPLAYER')
        params['cbr'] = player_args.get('cbr', 'Chrome')
        params['cbrver'] = player_args.get('cbrver', '53.0.2785.143')
        params['cos'] = player_args.get('cos', 'Windows')
        params['cosver'] = player_args.get('cosver', '10.0')

        fallback_player_response = {}

        el_values = ['detailpage', 'embedded']
        for el_value in el_values:
            params['el'] = el_value
            response = requests.get('https://www.youtube.com/get_video_info', params=params,
                                    headers=headers, cookies=cookies, allow_redirects=True)
            response.encoding = 'utf-8'
            data = response.text

            parameters = dict(parse_qsl(data))
            playability_status['fallback'] = parameters.get('status', '') != 'fail'
            fallback_player_response = json.loads(parameters.get('player_response', '{}'))

            if (fallback_player_response.get('streamingData', {}).get('formats', []) or
                    fallback_player_response.get('streamingData', {}).get('hlsManifestUrl', '')):
                break

        if not player_response:
            player_response = fallback_player_response
            playability_status = player_response.get('playabilityStatus', {})

        playback_tracking = player_response.get('playbackTracking', {})
        captions = player_response.get('captions', {})
        video_details = player_response.get('videoDetails', {})
        is_live_content = video_details.get('isLiveContent') is True
        streaming_data = player_response.get('streamingData', {})

        live_url = (streaming_data.get('hlsManifestUrl', '') or
                    fallback_player_response.get('streamingData', {}).get('hlsManifestUrl', ''))
        is_live = is_live_content and live_url

        metadata = {
            'video': {},
            'channel': {},
            'images': {},
            'subtitles': []
        }

        metadata['video']['id'] = video_details.get('videoId', video_id)
        metadata['video']['title'] = video_details.get('title', u'').encode('utf-8')
        metadata['channel']['author'] = video_details.get('author', u'').encode('utf-8')
        metadata['channel']['id'] = video_details.get('channelId', '')

        for image_meta in self.image_map():
            image_url = 'https://i.ytimg.com/vi/{video_id}/{image}' \
                .format(video_id=video_id, image=image_meta['image'])

            if is_live:
                image_url = image_url.replace('.jpg', '_live.jpg')

            metadata['images'][image_meta['to']] = image_url

        microformat = player_response.get('microformat', {}).get('playerMicroformatRenderer', {})
        metadata['video']['status'] = {
            'unlisted': microformat.get('isUnlisted', False),
            'private': video_details.get('isPrivate', False),
            'crawlable': video_details.get('isCrawlable', False),
            'family_safe': microformat.get('isFamilySafe', False),
            'live': is_live,
        }

        status = self.playability(playability_status)
        if not status['playable']:
            raise Exception(status['reason'])

        metadata['subtitles'] = Subtitles(video_id, captions).retrieve()

        report = {
            'playback_url': '',
            'watchtime_url': ''
        }

        playback_url = playback_tracking.get('videostatsPlaybackUrl', {}).get('baseUrl', '')
        watchtime_url = playback_tracking.get('videostatsWatchtimeUrl', {}).get('baseUrl', '')

        if playback_url and playback_url.startswith('http'):
            report['playback_url'] = ''.join([
                playback_url,
                '&ver=2&fs=0&volume=100&muted=0',
                '&cpn={cpn}'.format(cpn=self.generate_cpn())
            ])

        if watchtime_url and watchtime_url.startswith('http'):
            report['watchtime_url'] = ''.join([
                watchtime_url,
                '&ver=2&fs=0&volume=100&muted=0',
                '&cpn={cpn}'.format(cpn=self.generate_cpn()),
                '&st={st}&et={et}&state={state}'
            ])

        cipher = None
        stream_info = {}

        adaptive_formats = streaming_data.get('adaptiveFormats', [])
        # standard_formats = streaming_data.get('formats', [])

        mpd_url = streaming_data.get('dashManifestUrl', '') or \
                  fallback_player_response.get('streamingData', {}).get('dashManifestUrl', '')

        license_data = {
            'url': None,
            'proxy': None,
            'token': None
        }

        license_infos = streaming_data.get('licenseInfos', [])
        for license_info in license_infos:
            if license_info.get('drmFamily') == 'WIDEVINE':
                license_data['url'] = license_info.get('url', None)
                if license_data['url']:
                    license_data['proxy'] = 'http://127.0.0.1:52520/widevine||R{SSM}|'
                    license_data['token'] = self._access_token
                    break

        if self.requires_cipher(adaptive_formats):
            javascript_url = \
                self.get_player_javascript(video_id, player_config.get('assets', {}).get('js', ''))
            cipher = Cipher(javascript_url)

        generated_manifest = False
        if not license_data.get('url') and not is_live:
            mpd_url, stream_info = ManifestGenerator(cipher).generate(
                video_id,
                adaptive_formats,
                video_details.get('lengthSeconds', '0')
            )
            generated_manifest = True

        if not generated_manifest and mpd_url:
            mpd_url = self._decipher_signature(cipher, mpd_url)
            if not mpd_url:
                raise Exception('Failed to decipher signature')

        video_stream = {
            'url': mpd_url,
            'metadata': metadata,
            'headers': curl_headers,
            'license': license_data,
            'report': report
        }

        if is_live:
            video_stream['url'] = '&'.join([video_stream['url'], 'start_seq=$START_NUMBER$'])
            video_stream.update(self.itags.get('9998'))
            return video_stream

        if not stream_info:
            video_stream.update(self.itags.get('9999'))
            return video_stream

        has_video = (stream_info['video']['codec'] != '' and
                     int(stream_info['video']['bandwidth']) > 0)
        if has_video:
            video_stream.update(self.itags.get('9999'))
            video_stream['video']['height'] = stream_info['video']['height']
            video_stream['video']['encoding'] = stream_info['video']['codec']
        else:
            video_stream.update(self.itags.get('9997'))

        video_stream['audio']['encoding'] = stream_info['audio']['codec']
        if int(stream_info['audio'].get('bitrate', 0)) > 0:
            video_stream['audio']['bitrate'] = int(stream_info['audio'].get('bitrate', 0))

        if stream_info['video']['quality_label']:
            video_stream['title'] = stream_info['video']['quality_label']
            return video_stream

        if has_video:
            video_stream['title'] = '%sp%s' % \
                                    (stream_info['video']['height'],
                                     stream_info['video']['fps'])
            return video_stream

        video_stream['title'] = '%s@%s' % \
                                (stream_info['audio']['codec'],
                                 str(stream_info['audio'].get('bitrate', 0)))
        return video_stream
