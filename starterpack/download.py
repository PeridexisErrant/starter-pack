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
    #pylint:disable=no-member

    def json(self, identifier):
        url = self.json_template.format(identifier)
        if url not in JSON_CACHE:
            JSON_CACHE[url] = requests.get(url).json()
        return JSON_CACHE[url]

    def version(self, identifier):
        return self.json(identifier)[self.version_key]

    def filename(self, identifier):
        raise NotImplementedError()

    def dl_link(self, identifier):
        raise NotImplementedError()


class DFFDMetadata(AbstractMetadata):
    def __init__(self):
        self.json_template = 'http://dffd.bay12games.com/file_data/{}.json'
        self.version_key = 'version'

    def filename(self, ID):
        return self.json(ID)['filename']

    def dl_link(self, ID):
        return 'http://dffd.bay12games.com/download.php?id={}&f=b'.format(ID)


class GitHubMetadata(AbstractMetadata):
    def __init__(self):
        self.json_template = 'https://api.github.com/repos/{}/releases/latest'
        self.version_key = 'name'
        self.stored = {}

    def dl_link(self, repo):
        """A release on Github can have several files associated with it."""
        if repo not in self.stored:
            assets = self.json(repo)['assets']
            if assets:
                assets.sort(key=lambda a: len(a['name']))
                win = [a for a in assets if 'win' in a['name'].lower()]
                win64 = [a for a in win if '64' in a['name']]
                lst = win64 if win64 else (win if win else assets)
                self.stored[repo] = lst[0]['browser_download_url']
            else:
                self.stored[repo] = self.json(repo)['zipball_url']
        return self.stored[repo]

    def filename(self, repo):
        fname = os.path.basename(self.dl_link(repo))
        if '/zipball/' in self.dl_link(repo):
            return '{}_{}_{}.zip'.format(repo.replace('/', '_'), fname)
        return fname
