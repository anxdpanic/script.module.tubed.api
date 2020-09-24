# -*- coding: utf-8 -*-
"""
    Copyright (C) 2020 Tubed API (script.module.tubed.api)

    This file is part of script.module.tubed.api

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only.txt for more information.
"""

import re
from copy import deepcopy
from urllib.parse import parse_qsl
from urllib.parse import unquote

import xbmcvfs  # pylint: disable=import-error

from .quality import Quality


class ManifestGenerator:
    path = xbmcvfs.translatePath('special://temp/script.module.tubed.api/')

    def __init__(self, itags, cipher):
        self._cipher = cipher
        self._itags = itags
        self._discarded = []

    @property
    def cipher(self):
        return self._cipher

    @property
    def itags(self):
        return self._itags

    @property
    def discarded(self):
        return self._discarded

    @discarded.setter
    def discarded(self, value):
        self._discarded.append(value)

    def _make_dirs(self):
        if not xbmcvfs.exists(self.path):
            _ = xbmcvfs.mkdirs(self.path)

        return xbmcvfs.exists(self.path)

    def discard_audio(self, fmt, mime_type, itag, stream, reason='unsupported'):
        discarded = {
            'audio': {
                'itag': str(itag),
                'mime': str(mime_type),
                'codec': str(stream['codec']),
                'bandwidth': int(stream['bandwidth'])
            },
            'reason': reason
        }

        match = re.search('codecs="(?P<codec>[^"]+)"', discarded['audio']['codec'])
        if match:
            discarded['audio']['codec'] = match.group('codec')

        if fmt:
            bitrate = int(fmt.get('audio', {}).get('bitrate', 0))
            if bitrate > 0:
                discarded['audio']['bitrate'] = bitrate

        self.discarded = discarded

    def discard_video(self, mime_type, itag, stream, reason='unsupported'):
        discarded = {
            'video': {
                'itag': str(itag),
                'width': str(stream['width']),
                'height': str(stream['height']),
                'fps': str(stream['frameRate']),
                'codec': str(stream['codec']),
                'mime': str(mime_type),
                'bandwidth': int(stream['bandwidth'])
            },
            'reason': reason
        }

        match = re.search('codecs="(?P<codec>[^"]+)"', discarded['video']['codec'])
        if match:
            discarded['video']['codec'] = match.group('codec')

        if stream.get('quality_label'):
            discarded['video']['quality_label'] = str(stream['quality_label'])

        self.discarded = discarded

    def _filter_qualities(self, stream_data, container, quality_object):  # pylint: disable=too-many-branches
        data = deepcopy(stream_data)

        if container == 'mp4':
            discard_mime = 'video/webm'
            mime_type = 'video/mp4'
        elif container == 'webm':
            discard_mime = 'video/mp4'
            mime_type = 'video/webm'
        else:
            return data

        if quality_object.limit_30fps and mime_type in stream_data:
            # if 30 fps limit enabled, discard streams that are greater than 30fps
            if any(itag for itag in data[mime_type].keys() if data[mime_type][itag]['fps'] <= 30):
                for itag in list(data[mime_type].keys()):
                    if data[mime_type][itag]['fps'] > 30:
                        self.discard_video(mime_type, itag, data[mime_type][itag], 'frame rate')
                        del data[mime_type][itag]

        if discard_mime in data:
            # discard streams with unwanted mime type
            for itag in list(data[discard_mime].keys()):
                self.discard_video(discard_mime, itag, data[discard_mime][itag], 'mime type')
                del data[discard_mime][itag]

            del data[discard_mime]

        itag_matches = []
        itag_match = None

        for quality in quality_object.qualities:
            # find all streams with matching height
            if any(itag for itag in list(data[mime_type].keys())
                   if int(data[mime_type][itag].get('height', 0)) == quality):
                i_matches = [itag for itag in list(data[mime_type].keys())
                             if int(data[mime_type][itag].get('height', 0)) == quality]
                itag_matches.extend(i_matches)
                break

        if not itag_matches:
            # find best match for quality if there were no exact height candidates
            for index, quality in enumerate(quality_object.qualities):
                if index == len(quality_object.qualities) - 1:
                    continue

                if any(itag for itag in data[mime_type].keys()
                       if (quality > int(data[mime_type][itag].get('height', 0)) >=
                           quality_object.qualities[index + 1])):
                    i_match = next(itag for itag in data[mime_type].keys()
                                   if ((int(data[mime_type][itag].get('height', 0)) < quality) and
                                       (int(data[mime_type][itag].get('height', 0)) >=
                                        quality_object.qualities[index + 1])))
                    itag_matches.append(i_match)
                    break

        for itag in list(data[mime_type].keys()):
            # find highest fps and bandwidth itag out of all candidates
            if itag in itag_matches:
                if (not itag_match or itag_match.get('fps') < data[mime_type][itag].get('fps') or
                        (itag_match.get('fps') == data[mime_type][itag].get('fps') and
                         itag_match.get('bandwidth') < data[mime_type][itag].get('bandwidth'))):
                    itag_match = data[mime_type][itag]

        if itag_match:
            for itag in list(data[mime_type].keys()):
                # discard all streams except the best match
                if itag != itag_match.get('id'):
                    self.discard_video(mime_type, itag, data[mime_type][itag], 'quality')
                    del data[mime_type][itag]

        return data

    def _stream_data(self, formats):
        data = {}
        for item in formats:
            stream_map = item

            stream_map.update(dict(parse_qsl(item.get('signatureCipher', item.get('cipher', '')))))
            stream_map['itag'] = str(stream_map.get('itag'))

            mime_type = stream_map.get('mimeType')
            mime_type = unquote(mime_type)

            mime = mime_type.split(';')[0]
            itag = stream_map.get('itag')

            if mime not in data:
                data[mime] = {}
            data[mime][itag] = {}

            codec = str(mime_type[1][1:])
            data[mime][itag]['codec'] = codec

            match = re.search('codecs="(?P<codec>[^"]+)"', codec)
            if match:
                data[mime][itag]['codec'] = match.group('codec')

            data[mime][itag]['id'] = itag

            data[mime][itag]['width'] = stream_map.get('width')
            data[mime][itag]['height'] = stream_map.get('height')

            data[mime][itag]['quality_label'] = str(stream_map.get('qualityLabel'))

            data[mime][itag]['bandwidth'] = stream_map.get('bitrate', 0)

            # map frame rates to a more common representation to
            # lessen the chance of double refresh changes sometimes
            # 30 fps is 30 fps, more commonly it is 29.97 fps (same for all mapped frame rates)
            frame_rate = None
            fps_scale_map = {
                24: 1001,
                30: 1001,
                60: 1001
            }

            if 'fps' in stream_map:
                fps = int(stream_map.get('fps'))
                data[mime][itag]['fps'] = fps
                scale = fps_scale_map.get(fps, 1000)
                frame_rate = '%d/%d' % (fps * 1000, scale)

            data[mime][itag]['frameRate'] = frame_rate

            url = unquote(stream_map.get('url'))

            signature_parameter = '&signature='
            if 'sp' in stream_map:
                signature_parameter = '&%s=' % stream_map['sp']

            if 'sig' in stream_map:
                url = ''.join([url, signature_parameter, stream_map['sig']])

            elif 's' in stream_map:
                url = ''.join([url, signature_parameter, self.cipher.signature(stream_map['s'])])

            url = url.replace("&", "&amp;").replace('"', "&quot;")
            url = url.replace("<", "&lt;").replace(">", "&gt;")

            data[mime][itag]['baseUrl'] = url

            data[mime][itag]['indexRange'] = '0-0'
            data[mime][itag]['initRange'] = '0-0'

            if 'indexRange' in stream_map and 'initRange' in stream_map:
                data[mime][itag]['indexRange'] = \
                    '-'.join([stream_map.get('indexRange').get('start'),
                              stream_map.get('indexRange').get('end')])

                data[mime][itag]['init'] = \
                    '-'.join([stream_map.get('initRange').get('start'),
                              stream_map.get('initRange').get('end')])

            if ('indexRange' not in stream_map or
                    'initRange' not in stream_map or
                    data[mime][itag].get('indexRange') == '0-0' and
                    data[mime][itag].get('initRange') == '0-0'):

                if mime.startswith('video'):
                    self.discard_video(mime, itag, data[mime][itag], 'no init or index')

                else:
                    stream_format = self.itags.get(itag, {})
                    self.discard_audio(stream_format, mime, itag,
                                       data[mime][itag], 'no init or index')

                del data[mime][itag]

        return data

    def _filter_hdr(self, data, hdr=False):
        data = deepcopy(data)
        webm = {}

        if hdr and any(itag for itag in data.keys()
                       if 'vp9.2' in data[itag]['codec']):
            # when hdr enabled and available replace vp9 streams with vp9.2 (hdr)
            for itag in data.keys():
                if 'vp9.2' in data[itag]['codec']:
                    webm[itag] = data[itag]

            discarded = [data[itag] for itag in (set(data) - set(webm)) if itag in data]

            for discard in discarded:
                self.discard_video('video/webm', discard['id'],
                                   data[discard['id']], 'replaced by hdr')

        elif not hdr:
            # when hdr disabled and remove vp9.2 (hdr) streams
            for itag in data.keys():
                if 'vp9' in data[itag]['codec']:
                    webm[itag] = data[itag]

            discarded = [data[itag] for itag in (set(data) - set(webm)) if itag in data]

            for discard in discarded:
                self.discard_video('video/webm', discard['id'],
                                   data[discard['id']], 'hdr disabled')

        return webm

    @staticmethod
    def _stream_info_template():
        return {
            'video': {
                'height': '0',
                'fps': '0',
                'codec': '',
                'mime': '',
                'quality_label': '',
                'bandwidth': 0
            },
            'audio': {
                'bitrate': '0',
                'codec': '',
                'mime': '',
                'bandwidth': 0
            }
        }

    def generate(self, video_id, formats, duration, quality_object=None):  # pylint: disable=too-many-branches,too-many-statements
        if not self._make_dirs():
            return None

        if not quality_object:
            quality_object = Quality('mp4')

        has_video_stream = False

        stream_info = self._stream_info_template()
        data = self._stream_data(formats)

        if not data.get('video/mp4') and not data.get('video/webm'):
            return None, None

        default_mime_type = 'mp4'
        supported_mime_types = []

        if data.get('video/mp4'):
            supported_mime_types.append('video/mp4')

        if data.get('audio/mp4'):
            supported_mime_types.append('audio/mp4')

        if any(mime for mime in data if mime == 'video/webm') and data.get('video/webm'):
            supported_mime_types.append('video/webm')

        if ('video/webm' in supported_mime_types and
                ((isinstance(quality_object.quality, str) and quality_object.quality == 'webm') or
                 (isinstance(quality_object.quality, int) and quality_object.quality > 1080) or
                 quality_object.hdr)):
            default_mime_type = 'webm'

        if 'video/webm' in supported_mime_types:
            filtered = self._filter_hdr(data['video/webm'], hdr=quality_object.hdr)
            if filtered:
                data['video/webm'] = filtered

        if isinstance(quality_object.quality, int) and isinstance(quality_object.qualities, list):
            data = self._filter_qualities(data, default_mime_type, quality_object)

        mpd_list = ['<?xml version="1.0" encoding="UTF-8"?>\n'
                    '<MPD xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
                    'xmlns="urn:mpeg:dash:schema:mpd:2011" '
                    'xmlns:xlink="http://www.w3.org/1999/xlink" '
                    'xsi:schemaLocation="urn:mpeg:dash:schema:mpd:2011 '
                    'http://standards.iso.org/ittf/PubliclyAvailableStandards/'
                    'MPEG-DASH_schema_files/DASH-MPD.xsd" '
                    'minBufferTime="PT1.5S" mediaPresentationDuration="PT', duration,
                    'S" type="static" profiles="urn:mpeg:dash:profile:isoff-main:2011">\n',
                    '\t<Period>\n']

        adaptation_set_idx = 0
        for mime in data:  # pylint: disable=too-many-nested-blocks
            if mime in supported_mime_types:
                default = False
                if mime.endswith(default_mime_type):
                    default = True

                mpd_list.append(''.join(['\t\t<AdaptationSet id="', str(adaptation_set_idx),
                                         '" mimeType="', mime,
                                         '" subsegmentAlignment="true" subsegmentStartsWithSAP="1" '
                                         'bitstreamSwitching="true" default="',
                                         str(default).lower(), '">\n']))

                mpd_list.append('\t\t\t<Role schemeIdUri="urn:mpeg:DASH:role:2011" '
                                'value="main"/>\n')

                for itag in data[mime]:
                    stream_format = self.itags.get(itag, {})
                    if 'audio' in mime:

                        audio_codec = data[mime][itag]['codec']
                        if audio_codec.lower() == 'opus':
                            self.discard_audio(stream_format, mime, itag, data[mime][itag])
                            continue

                        if audio_codec.lower() == 'vorbis':
                            self.discard_audio(stream_format, mime, itag, data[mime][itag])
                            continue

                        if (int(data[mime][itag]['bandwidth']) >
                                int(stream_info['audio']['bandwidth'])):

                            stream_info['audio']['mime'] = str(mime)
                            if stream_format:

                                bitrate = int(stream_format.get('audio', {}).get('bitrate', 0))
                                if bitrate > 0:
                                    stream_info['audio']['bitrate'] = bitrate

                                stream_info['audio']['codec'] = \
                                    stream_format.get('audio', {}).get('encoding')

                            if not stream_info['audio'].get('codec'):
                                stream_info['audio']['codec'] = audio_codec

                            stream_info['audio']['bandwidth'] = int(data[mime][itag]['bandwidth'])

                        mpd_list.append(''.join(['\t\t\t<Representation id="',
                                                 itag, '" ', data[mime][itag]['codec'],
                                                 ' bandwidth="', str(data[mime][itag]['bandwidth']),
                                                 '">\n']))

                        mpd_list.append('\t\t\t\t<AudioChannelConfiguration '
                                        'schemeIdUri="urn:mpeg:dash:23003:3:'
                                        'audio_channel_configuration:2011" value="2"/>\n')

                    else:
                        video_codec = data[mime][itag]['codec']

                        if video_codec.lower() == 'vp9.2' and not quality_object.hdr:
                            self.discard_video(mime, itag, data[mime][itag], 'hdr not selected')
                            continue

                        if (video_codec.lower().startswith(('av01', 'av1')) and
                                not quality_object.av1):
                            self.discard_video(mime, itag, data[mime][itag], 'av1 not selected')
                            continue

                        has_video_stream = True
                        if default:
                            if (int(data[mime][itag]['bandwidth']) >
                                    int(stream_info['video']['bandwidth'])):
                                stream_info['video']['height'] = str(data[mime][itag]['height'])
                                stream_info['video']['fps'] = str(data[mime][itag]['frameRate'])
                                stream_info['video']['mime'] = str(mime)
                                stream_info['video']['codec'] = video_codec
                                stream_info['video']['bandwidth'] = \
                                    int(data[mime][itag]['bandwidth'])

                                if data[mime][itag].get('quality_label'):
                                    stream_info['video']['quality_label'] = \
                                        str(data[mime][itag]['quality_label'])

                                if stream_format:
                                    stream_info['video']['codec'] = \
                                        stream_format.get('video', {}).get('encoding')

                                if not stream_info['video'].get('codec'):
                                    stream_info['video']['codec'] = video_codec

                        video_codec = data[mime][itag]['codec']
                        mpd_list.append(''.join(['\t\t\t<Representation id="', itag, '" ',
                                                 video_codec, ' startWithSAP="1" bandwidth="',
                                                 str(data[mime][itag]['bandwidth']), '" width="',
                                                 str(data[mime][itag]['width']), '" height="',
                                                 str(data[mime][itag]['height']), '" frameRate="',
                                                 str(data[mime][itag]['frameRate']), '">\n']))

                    mpd_list.append(''.join(['\t\t\t\t<BaseURL>',
                                             data[mime][itag]['baseUrl'],
                                             '</BaseURL>\n']))

                    mpd_list.append(''.join(['\t\t\t\t<SegmentBase indexRange="',
                                             data[mime][itag]['indexRange'],
                                             '">\n', '\t\t\t\t\t\t<Initialization range="',
                                             data[mime][itag]['init'], '" />\n',
                                             '\t\t\t\t</SegmentBase>\n']))

                    mpd_list.append('\t\t\t</Representation>\n')
                mpd_list.append('\t\t</AdaptationSet>\n')

                adaptation_set_idx = adaptation_set_idx + 1

            else:
                for i in data[mime]:
                    stream_format = self.itags.get(i, {})
                    if 'audio' in mime:
                        self.discard_audio(stream_format, mime, i, data[mime][i])

                    else:
                        self.discard_video(mime, i, data[mime][i])

        mpd_list.append('\t</Period>\n</MPD>\n')
        manifest_contents = ''.join(mpd_list)

        if self.discarded:
            self.discarded = sorted(
                self.discarded,
                key=lambda k: k.get('audio', k.get('video', {}))['bandwidth'],
                reverse=True
            )

        if not has_video_stream:
            pass

        filename = '{path}{video_id}.mpd'.format(path=self.path, video_id=video_id)
        try:
            with xbmcvfs.File(filename, 'w') as open_file:
                _ = open_file.write(str(manifest_contents))

            return 'http://127.0.0.1:52520/{video_id}.mpd'.format(video_id=video_id), stream_info

        except:  # pylint: disable=bare-except
            return None, None
