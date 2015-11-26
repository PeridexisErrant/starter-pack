"""Provides abstractions over metadata storage and downloading.

 - Download metadata from file hosts, or open local cache
 - Download any missing files
 - Provide a common 'Component' object with various config methods

This should be the only module that touches the network or which components
are described in config.yml
"""
#pylint:disable=missing-docstring

import json
import os
import time
import yaml

import requests

# TODO:  use caching decorator, general cleanup and refactoring

with open('config.yml') as ymlfile:
    YML = yaml.safe_load(ymlfile)

try:
    with open('_cached.json') as f:
        JSON_CACHE = json.load(f)
    print('Loaded metadata from local "_cache.json"; delete to refresh.\n')
except IOError:
    JSON_CACHE = {}
    print('Could not load metadata from cache; will download from APIs...\n')


class AbstractMetadata(object):
    """Base class for site-specific downloaders."""
    def json(self, identifier):
        raise NotImplementedError()
    def filename(self, identifier):
        return self.json(identifier)['filename']
    def dl_link(self, identifier):
        return self.json(identifier)['dl_link']
    def version(self, identifier):
        return self.json(identifier)['version']
    def days_since_update(self, identifier):
        raise NotImplementedError()


class DFFDMetadata(AbstractMetadata):

    def json(self, ID):
        url = 'http://dffd.bay12games.com/file_data/{}.json'.format(ID)
        if url not in JSON_CACHE:
            JSON_CACHE[url] = requests.get(url).json()
        return JSON_CACHE[url]

    def dl_link(self, ID):
        return 'http://dffd.bay12games.com/download.php?id={}&f=b'.format(ID)

    def days_since_update(self, ID):
        secs = time.time() - int(self.json(ID)['updated_timestamp'])
        return int(secs / (60 * 60 * 24))


class GitHubMetadata(AbstractMetadata):

    def json(self, repo):
        if repo in JSON_CACHE:
            return JSON_CACHE[repo]
        # Abstract the release/tag differences here if possible
        url = 'https://api.github.com/repos/{}/releases/latest'.format(repo)
        release = requests.get(url).json()
        if release.get('assets'):
            assets = sorted(release['assets'], key=lambda a: len(a['name']))
            win = [a for a in assets if 'win' in a['name'].lower()]
            win64 = [a for a in win if '64' in a['name']]
            lst = win64 if win64 else (win if win else assets)
            release['dl_link'] = lst[0]['browser_download_url']
            release['filename'] = os.path.basename(release['dl_link'])
            for key in ['author', 'body', 'assets']:
                release.pop(key)
            data = release
        else:
            tags_url = 'https://api.github.com/repos/{}/tags'.format(repo)
            tag = requests.get(tags_url).json()[0]
            tag['dl_link'] = tag['zipball_url']
            tag['filename'] = '{}_{}.zip'.format(
                repo.replace('/', '_'), os.path.basename(tag['dl_link']))
            tag['published_at'] = requests.get(
                tag['commit']['url']).json()['commit']['author']['date']
            data = tag
        data['version'] = data['name']
        JSON_CACHE[repo] = data
        return JSON_CACHE[repo]

    def days_since_update(self, ID): # "2015-11-23T09:52:07Z"
        update_epoch = time.mktime(time.strptime(
            self.json(ID)['published_at'], '%Y-%m-%dT%H:%M:%SZ'))
        return int((time.time() - update_epoch) / (60 * 60 * 24))


class ManualMetadata(AbstractMetadata):
    """Mock metadata API for locally configured components."""
    def json(self, identifier):
        for category in YML.values():
            if identifier in category:
                return category[identifier]

    def dl_link(self, identifier):
        return self.json(identifier)['dl_link']

    def filename(self, identifier):
        return os.path.basename(self.dl_link(identifier))

    def days_since_update(self, ID):
        return -1


class Component(object):
    """Represent a downloadable component, with metadata."""
    #pylint:disable=too-many-instance-attributes,too-few-public-methods

    def __init__(self, category, item):
        self.config = YML[category][item]
        self.category = category
        self.name = item
        self.bay12 = str(self.config.get('bay12', 126076))
        self.thread = ('http://www.bay12forums.com/smf/index.php?topic=' +
                       self.bay12)
        self.ident = (self.name if self.config['host'] == 'manual'
                      else self.config['ident'])
        metadata = {'dffd': DFFDMetadata,
                    'github': GitHubMetadata,
                    'manual': ManualMetadata}[self.config['host']]()
        self.dl_link = metadata.dl_link(self.ident)
        self.filename = metadata.filename(self.ident)
        self.version = metadata.version(self.ident)
        self.days_since_update = metadata.days_since_update(self.ident)
        self.path = os.path.join('components', self.filename)
        if item == 'Dwarf Fortress':
            # TODO: check version and release date via the rss feed
            # http://bay12games.com/dwarves/dev_release.rss
            pass

    def download(self):
        """Ensure that the given file is downloaded to the components dir."""
        if os.path.isfile(self.path):
            return False
        print('downloading {}...'.format(self.name))
        buf = b''.join(requests.get(self.dl_link).iter_content(1024))
        with open(self.path, 'wb') as f:
            f.write(buf)
        return True


__items = [(c, i) for c, vals in YML.items() for i in vals if c != 'version']

COMPONENTS = tuple(Component(k, i) for k, i in __items)

ALL = {c.name: c for c in COMPONENTS}

UTILITIES = tuple(c for c in COMPONENTS if c.category == 'utilities')
GRAPHICS = tuple(c for c in COMPONENTS if c.category == 'graphics')
FILES = tuple(c for c in COMPONENTS if c.category == 'files')

print('Component:           Age:   Version:       Filename:')
for comp in sorted(COMPONENTS, key=lambda c: c.days_since_update):
    print(' {:22}{:3}   {:15}{:30}'.format(
        comp.name[:19], comp.days_since_update,
        comp.version, comp.filename[:30]))

with open('_cached.json', 'w') as cachefile:
    json.dump(JSON_CACHE, cachefile, indent=4)
