"""Classes for interaction with web APIs for component metadata."""
# pylint:disable=missing-docstring

import datetime
import os
import sys
import time

import requests
import yaml


# duplicate of paths.HOST_OS to avoid import loop
_os = {'win32': 'win', 'cygwin': 'win',
       'darwin': 'osx', 'linux': 'linux'}[sys.platform]


def get_ok(*args, **kwargs):
    """requests.get plus raise_for_status"""
    r = requests.get(*args, **kwargs)
    r.raise_for_status()
    return r


def get_auth():
    """Return user auth to increase GitHub API rate limit."""
    # TODO:  support OAuth?  (see issue #2)
    if os.path.isfile('_CRED'):
        with open('_CRED') as f:
            return tuple(f.read().split())
    return None


def cache(method=lambda *_: None, *, saved={}, dump=False):
    """A local cache is faster, and avoids GitHub API ratelimit."""
    # TODO:  split cache by '_os' key
    if not saved:
        saved['notified'] = True
        try:
            if time.time() - os.path.getmtime('_cached.yml') < 60*60:
                with open('_cached.yml') as f:
                    saved.update(yaml.load(f))
                print('Loaded metadata from "_cached.yml".\n')
            else:
                print('Cache expired, downloading latest metadata.\n')
                os.remove('_cached.yml')
        except IOError:
            print('No metadata cache; will download from APIs.\n')
    elif dump and not os.path.isfile('_cached.yml'):
        with open('_cached.yml', 'w') as f:
            yaml.dump(saved, f, indent=4)

    def wrapper(self, ident):
        if ident not in saved:
            saved[ident] = method(self, ident)
        return saved[ident]
    return wrapper


def days_ago(func):
    """Moves date-subtraction boilerplate to a decorator."""
    def _inner(*args):
        return (datetime.datetime.today() - func(*args)).days
    return _inner


def best_asset(fname_list):
    """Picks the preferred asset from the list."""
    # Support non-64bit preference at some point?
    os_files = [a for a in fname_list if _os in os.path.basename(a).lower()]
    os64_files = [a for a in os_files if '64' in os.path.basename(a).lower()]
    return (os64_files or os_files or fname_list)[0]


class AbstractMetadata(object):
    """Base class for site-specific downloaders."""
    def json(self, identifier):
        raise NotImplementedError()

    def filename(self, identifier):
        return os.path.basename(self.dl_link(identifier))

    def dl_link(self, identifier):
        return self.json(identifier)['dl_link']

    def version(self, identifier):
        return self.json(identifier)['version']

    def days_since_update(self, identifier):
        raise NotImplementedError()


class DFFDMetadata(AbstractMetadata):
    @cache
    def json(self, ID):
        return get_ok(
            'http://dffd.bay12games.com/file_data/{}.json'.format(ID)).json()

    def filename(self, ID):
        return self.json(ID)['filename']

    def dl_link(self, ID):
        return 'http://dffd.bay12games.com/download.php?id={}&f=b'.format(ID)

    @days_ago
    def days_since_update(self, ID):
        return datetime.datetime.fromtimestamp(
            float(self.json(ID)['updated_timestamp']))


class GitHubMetadata(AbstractMetadata):
    @cache
    def json(self, repo):
        url = 'https://api.github.com/repos/{}/releases'.format(repo)
        release = get_ok(url, auth=get_auth()).json()[0]
        assets = [r['browser_download_url'] for r in release['assets']]
        return {'version': release['tag_name'].strip(),
                'published_at': release['published_at'],
                'dl_link': best_asset(assets)}

    @days_ago
    def days_since_update(self, repo):
        return datetime.datetime.strptime(
            self.json(repo)['published_at'], '%Y-%m-%dT%H:%M:%SZ')


class GitHubTagMetadata(GitHubMetadata):
    @cache
    def json(self, repo):
        url = 'https://api.github.com/repos/{}/tags'.format(repo)
        tag = get_ok(url, auth=get_auth()).json()[0]
        pubdate = get_ok(tag['commit']['url'], auth=get_auth())
        return {'version': tag['name'], 'dl_link': tag['zipball_url'],
                'published_at': pubdate.json()['commit']['author']['date']}

    def filename(self, repo):
        return '{}_{}.zip'.format(
            repo.replace('/', '_'), os.path.basename(self.dl_link(repo)))


class BitbucketMetadata(AbstractMetadata):
    @cache
    def json(self, repo):
        # Only works for repos with releases, but that's fine
        url = 'https://api.bitbucket.org/2.0/repositories/{}/downloads'
        dls = get_ok(url.format(repo)).json().get('values', [])
        assets = [(v['links']['self']['href'], v['created_on']) for v in dls]
        best = best_asset([a for a, _ in assets])
        return {'dl_link': best, 'created_on': dict(assets)[best]}

    def version(self, repo):
        base = self.filename(repo).replace('PyLNP_', '')
        return base.split('.')[0].split('-')[0]  # from first '-' to first '.'

    @days_ago
    def days_since_update(self, repo):
        return datetime.datetime.strptime(
            self.json(repo)['created_on'].split('.')[0], '%Y-%m-%dT%H:%M:%S')


class ManualMetadata(AbstractMetadata):
    def json(self, identifier):
        with open('components.yml') as f:
            for category in yaml.safe_load(f).values():
                if identifier in category:
                    return category[identifier]

    @days_ago
    def days_since_update(self, ID):
        return self.json(ID)['updated'].date()


class DFMetadata(AbstractMetadata):
    @cache
    def json(self, df):
        url = 'http://bay12games.com/dwarves/dev_release.rss'
        for line in get_ok(url).text.split('\n'):
            if '<title>' in line and df not in line:
                return line[13:35].split(': DF ')

    def dl_link(self, df):
        url = 'http://bay12games.com/dwarves/df_{}_{}_{}.{}'
        tail = {'win': 'zip'}.get(_os, 'tar.bz2')
        _, vmaj, vmin = self.version(df).split('.')
        return url.format(vmaj, vmin, _os, tail)

    def version(self, df):
        return self.json(df)[1].strip()

    @days_ago
    def days_since_update(self, df):
        return datetime.datetime.strptime(self.json(df)[0], '%Y-%m-%d')


METADATA_TYPES = {
    'dffd': DFFDMetadata,
    'github': GitHubMetadata,
    'github/tag': GitHubTagMetadata,
    'bitbucket': BitbucketMetadata,
    'manual': ManualMetadata,
    'special': DFMetadata,
    }
