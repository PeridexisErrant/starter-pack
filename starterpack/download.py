"""Handles checking metadata and downloading files.

Support for DFFD is pretty good, GitHub is OK, and other sites can be done
manually - those two cover most of my content.
"""
#pylint:disable=missing-docstring

import json
import os
import requests

try:
    with open('_cached.json') as f:
        JSON_CACHE = json.load(f)
except IOError:
    JSON_CACHE = {}


def download(url):
    """Return the file contents for the given link."""
    return b''.join(requests.get(url, stream=True).iter_content(1024))


class AbstractMetadata(object):
    """Base class for site-specific downloaders."""
    def json(self, identifier):
        raise NotImplementedError()
    def filename(self, identifier):
        raise NotImplementedError()
    def dl_link(self, identifier):
        raise NotImplementedError()
    def version(self, identifier):
        return self.json(identifier)['version']


class DFFDMetadata(AbstractMetadata):

    def json(self, ID):
        url = 'http://dffd.bay12games.com/file_data/{}.json'.format(ID)
        if url not in JSON_CACHE:
            JSON_CACHE[url] = requests.get(url).json()
        return JSON_CACHE[url]

    def filename(self, ID):
        return self.json(ID)['filename']

    def dl_link(self, ID):
        return 'http://dffd.bay12games.com/download.php?id={}&f=b'.format(ID)


class GitHubMetadata(AbstractMetadata):

    def json(self, repo):
        url = 'https://api.github.com/repos/{}/releases/latest'.format(repo)
        tags_url = 'https://api.github.com/repos/{}/tags'.format(repo)
        if repo not in JSON_CACHE:
            # Get data
            tags = requests.get(tags_url).json()
            data = {} if not tags else tags[0]
            data.update(requests.get(url).json())
            # discard large-but-unused parts, to make the cache human-readable
            data['author'] = ''  # details of the user
            data['body'] = ''  # release notes
            for a in data.get('assets', []):
                a['uploader'] = ''
            JSON_CACHE[repo] = data
        return JSON_CACHE[repo]

    def version(self, identifier):
        return self.json(identifier)['name']

    def dl_link(self, repo):
        """A release on Github can have several files associated with it.
        If there's no release, get the zipball at the latest tag."""
        assets = self.json(repo).get('assets')
        if assets:
            assets.sort(key=lambda a: len(a['name']))
            win = [a for a in assets if 'win' in a['name'].lower()]
            win64 = [a for a in win if '64' in a['name']]
            lst = win64 if win64 else (win if win else assets)
            return lst[0]['browser_download_url']
        return self.json(repo)['zipball_url']

    def filename(self, repo):
        fname = os.path.basename(self.dl_link(repo))
        if '/zipball/' in self.dl_link(repo):
            return '{}_{}.zip'.format(repo.replace('/', '_'), fname)
        return fname
