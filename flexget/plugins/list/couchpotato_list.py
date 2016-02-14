from __future__ import unicode_literals, division, absolute_import

import logging
from urlparse import urlparse

import requests
from requests import RequestException

from flexget import plugin
from flexget.entry import Entry
from flexget.event import event

log = logging.getLogger('couchpotato_list')


class CouchPotatoList(object):
    schema = {
        'type': 'object',
        'properties': {
            'base_url': {'type': 'string'},
            'port': {'type': 'number', 'default': 80},
            'api_key': {'type': 'string'},
            'include_data': {'type': 'boolean', 'default': False}
        },
        'required': ['api_key', 'base_url'],
        'additionalProperties': False
    }

    @staticmethod
    def movie_list_request(base_url, port, api_key):
        parsedurl = urlparse(base_url)
        log.debug('Received movie list request')
        return '%s://%s:%s%s/api/%s/movie.list?status=active' % (
            parsedurl.scheme, parsedurl.netloc, port, parsedurl.path, api_key)

    @staticmethod
    def profile_list_request(base_url, port, api_key):
        parsedurl = urlparse(base_url)
        log.debug('Received profile list request')
        return '%s://%s:%s%s/api/%s/profile.list' % (
            parsedurl.scheme, parsedurl.netloc, port, parsedurl.path, api_key)

    @staticmethod
    def build_url(base_url, request_type, port, api_key):
        if request_type == 'active':
            return CouchPotatoList.movie_list_request(base_url, port, api_key)
        elif request_type == 'profiles':
            return CouchPotatoList.profile_list_request(base_url, port, api_key)
        else:
            raise plugin.PluginError('Received unknown API request, aborting.')

    @staticmethod
    def get_json(url):
        try:
            return requests.get(url).json()
        except RequestException as e:
            raise plugin.PluginError('Unable to connect to Couchpotato at %s. Error: %s' % (url, e))

    @staticmethod
    def quality_requirement_builder(quality_profile):
        """
        Converts CP's quality profile to a format that can be converted to FlexGet QualityRequirement
        """
        # TODO: Not all values have exact matches in flexget, need to update flexget qualities
        sources = {'BR-Disk': 'remux',  # Not a perfect match, but as close as currently possible
                   'brrip': 'bluray',
                   'dvdr': 'dvdrip',  # Not a perfect match, but as close as currently possible
                   'dvdrip': 'dvdrip',
                   'scr': 'dvdscr',
                   'r5': 'r5',
                   'tc': 'tc',
                   'ts': 'ts',
                   'cam': 'cam'}

        resolutions = {'1080p': '1080p',
                       '720p': '720p'}

        # Separate strings are needed for each QualityComponent
        # TODO list is converted to set because if a quality has 3d type in CP, it gets duplicated during the conversion
        # TODO when (and if) 3d is supported in flexget this will be needed to removed
        res_string = '|'.join(
            set([resolutions[quality] for quality in quality_profile['qualities'] if quality in resolutions]))
        source_string = '|'.join(
            set([sources[quality] for quality in quality_profile['qualities'] if quality in sources]))

        quality_requirement = (res_string + ' ' + source_string).rstrip()
        log.debug('quality requirement is %s' % quality_requirement)
        return quality_requirement

    @staticmethod
    def list_entries(config, test_mode=None):
        log.verbose('Connection to CouchPotato to retrieve movie list.')
        active_movies_url = CouchPotatoList.build_url(config.get('base_url'), 'active', config.get('port'),
                                                      config.get('api_key'))
        active_movies_json = CouchPotatoList.get_json(active_movies_url)
        # Gets profile and quality lists if include_data is TRUE
        if config.get('include_data'):
            log.verbose('Connection to CouchPotato to retrieve movie data.')
            profile_url = CouchPotatoList.build_url(config.get('base_url'), 'profiles', config.get('port'),
                                                    config.get('api_key'))
            profile_json = CouchPotatoList.get_json(profile_url)

        entries = []
        for movie in active_movies_json['movies']:
            quality_req = ''
            if movie['status'] == 'active':
                if config.get('include_data') and profile_json:
                    for profile in profile_json['list']:
                        if profile['_id'] == movie['profile_id']:  # Matches movie profile with profile JSON
                            quality_req = CouchPotatoList.quality_requirement_builder(profile)
                entry = Entry(title=movie["title"],
                              url='',
                              imdb_id=movie['info'].get('imdb'),
                              tmdb_id=movie['info'].get('tmdb_id'),
                              quality_req=quality_req)
                if entry.isvalid():
                    log.debug('adding entry %s' % entry)
                    entries.append(entry)
                else:
                    log.error('Invalid entry created? %s' % entry)
                    continue
                # Test mode logging
                if entry and test_mode:
                    log.info("Test mode. Entry includes:")
                    for key, value in entry.items():
                        log.info('     %s: %s' % (key.capitalize(), value))

        return entries

    def on_task_input(self, task, config):
        return self.list_entries(config)


@event('plugin.register')
def register_plugin():
    plugin.register(CouchPotatoList, 'couchpotato_list', api_ver=2, groups=['list'])
