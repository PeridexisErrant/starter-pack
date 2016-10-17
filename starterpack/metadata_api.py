"""Classes for interaction with web APIs for component metadata."""
# pylint:disable=missing-docstring

import datetime
import os
import time

import requests
import yaml

from . import paths


def get_ok(*args, **kwargs):
    """requests.get plus raise_for_status"""
    r = requests.get(*args, **kwargs)
    r.raise_for_status()
    return r


def get_auth():
    """Return user auth to increase GitHub API rate limit."""
    if os.path.isfile('_CRED'):
        with open('_CRED') as f:
            return tuple(f.read().split())
    return None


def cache(method=lambda *_: None, *, saved={}, dump=False):
    """A caching decorator.

    Reads cache from local file if cache is empty.
    Keeps record of when items were last refreshed, and expires at interval.
    Supports conditional requests for GitHub.
    """
    if not saved:
        try:
            with open('_cached.yml') as f:
                saved.update(yaml.load(f))
        except IOError:
            print('Downloading metadata for components...\n')
            saved.update({'metadata': {}, 'timestamps': {}})
    elif dump:
        with open('_cached.yml', 'w') as f:
            yaml.dump(saved, f, indent=4)

    def wrapper(self, ident):
        last_tstamp = saved.get('timestamps', {}).get(ident, 0)
        if (time.time() - last_tstamp) > 60*60:
            if not isinstance(self, GitHubAssetMetadata):
                saved['metadata'][ident] = method(self, ident)
            else:
                saved['metadata'][ident] = method(
                    self, ident, last_tstamp, saved['metadata'].get(ident))
            saved['timestamps'][ident] = time.time()
        return saved['metadata'][ident]
    return wrapper


def days_ago(func):
    """Moves date-subtraction boilerplate to a decorator."""
    def _inner(*args):
        return (datetime.datetime.today() - func(*args)).days
    return _inner


def best_asset(fname_list):
    """Return a dict of the best asset from the list for each OS."""
    def fname(a):
        return os.path.basename(a).lower()

    asst = {}
    for bits in ('32', '64'):
        wrong_bits = ['32', '64'][bits == '32']
        for platform in ('win', 'osx', 'linux'):
            os_files = [a for a in fname_list
                        if k in fname(a) or (k == 'osx' and 'mac' in fname(a))]
            un_bitted = [a for a in os_files if not wrong_bits in fname(a)]
            bitted = [a for a in os_files if bits in fname(a)]
            lst = bitted or un_bitted or os_files or fname_list
            asst[(platform, bits)] = lst[0] if lst else None
    return asst


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


class GitHubAssetMetadata(AbstractMetadata):
    # pylint:disable=arguments-differ
    @cache
    def json(self, repo, last_timestamp=None, last_json=None):
        """Return JSON payload, or None if not modified since timestamp."""
        url = 'https://api.github.com/repos/{}/releases/latest'.format(repo)
        header = {'If-Modified-Since': datetime.datetime.fromtimestamp(
            last_timestamp, datetime.timezone.utc).strftime(
                '%a, %d %b %Y %H:%M:%S GMT')}
        req = get_ok(url, auth=get_auth(), headers=header)
        if req.status_code == 304:
            return last_json
        resp = req.json()

        assets = [r['browser_download_url'] for r in resp['assets']]
        return {'version': resp['tag_name'].strip(),
                'published_at': resp['published_at'],
                'assets': best_asset(assets),
                'zipball_url': resp['zipball_url']}

    def dl_link(self, repo):
        return self.json(repo)['assets'][(paths.HOST_OS, paths.BITS)]

    @days_ago
    def days_since_update(self, repo):
        return datetime.datetime.strptime(
            self.json(repo)['published_at'], '%Y-%m-%dT%H:%M:%SZ')


class GitHubZipballMetadata(GitHubAssetMetadata):
    def dl_link(self, repo):
        return self.json(repo)['zipball_url']

    def filename(self, repo):
        return '{}_{}.zip'.format(
            repo.replace('/', '_'), os.path.basename(self.dl_link(repo)))


class BitbucketMetadata(AbstractMetadata):
    @cache
    def json(self, repo):
        # Only works for repos with releases, but that's fine
        dls = get_ok('https://api.bitbucket.org/2.0/repositories/' + repo +
                     '/downloads?pagelen=100').json().get('values', [])
        assets = [v['links']['self']['href'] for v in dls]
        best = best_asset(assets)
        times = dict(zip(assets, [v['created_on'] for v in dls]))
        times = {k: times[v] for k, v in best.items()}
        return {'assets': best, 'times': times}

    def version(self, repo):
        base = self.filename(repo).replace('PyLNP_', '').replace('tar.', '')
        return os.path.splitext(base)[0].split('-')[0]

    dl_link = GitHubAssetMetadata.dl_link

    @days_ago
    def days_since_update(self, repo):
        return datetime.datetime.strptime(
            self.json(repo)['times'][(paths.HOST_OS, paths.BITS)]
            .split('.')[0], '%Y-%m-%dT%H:%M:%S')


class ManualMetadata(AbstractMetadata):
    def json(self, identifier):
        with open('components.yml') as f:
            for category in yaml.safe_load(f).values():
                if identifier in category:
                    return category[identifier]

    @days_ago
    def days_since_update(self, ID):
        return self.json(ID)['updated'].date()


def df_dl_from_ver(ver):
    url = 'http://bay12games.com/dwarves/df_{}_{}_{}.{}'
    tail = 'zip' if paths.HOST_OS == 'win' else 'tar.bz2'
    _, vmaj, vmin = ver.split('.')
    platform = paths.HOST_OS
    if paths.BITS == '32':
        platform += '32'
    return url.format(vmaj, vmin, paths.HOST_OS, tail)


class DFMetadata(AbstractMetadata):
    @cache
    def json(self, df):
        url = 'http://bay12games.com/dwarves/dev_release.rss'
        for line in get_ok(url).text.split('\n'):
            if '<title>' in line and df not in line:
                return line[13:35].split(': DF ')

    def dl_link(self, df):
        return df_dl_from_ver(self.version(df))

    def version(self, df):
        return self.json(df)[1].strip()

    @days_ago
    def days_since_update(self, df):
        return datetime.datetime.strptime(self.json(df)[0], '%Y-%m-%d')


METADATA_TYPES = {
    'dffd': DFFDMetadata,
    'github-asset': GitHubAssetMetadata,
    'github-source': GitHubZipballMetadata,
    'bitbucket': BitbucketMetadata,
    'manual': ManualMetadata,
    'special': DFMetadata,
    }
