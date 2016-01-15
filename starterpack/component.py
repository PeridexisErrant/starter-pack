"""Provides abstractions over metadata storage and downloading.

 - Download metadata from file hosts, or open local cache
 - Download any missing files
 - Provide a common 'Component' object with various config methods

Any modules that use this data should just access the dict ALL (bottom).

This should be the only module that touches the network or which components
are described in config.yml
"""
#pylint:disable=missing-docstring

import collections
import concurrent.futures
import datetime
import os
import time
import yaml

import requests


def cache(method, *, saved={}, dump=False):
    """A local cache is faster, and avoids GitHub API ratelimit."""
    if not saved:
        saved['notified'] = True
        try:
            if time.time() - os.stat('_cached.yml').st_mtime < 60*60:
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


def report(comps=None):
    if comps is None:
        comps = ALL.values()
    print('Component:            Age:   Version:       Filename:')
    for comp in sorted(comps, key=lambda c: c.days_since_update):
        print(' {:22}{:4}   {:15}{:30}'.format(
            comp.name[:19], comp.days_since_update,
            comp.version, comp.filename[:30]))
    cache(lambda s, x: None, dump=True)


def raw_dl(url, path):
    """Save url contents to a file."""
    req = requests.get(url)
    req.raise_for_status()
    with open(path, 'wb') as f:
        f.write(b''.join(req.iter_content(1024)))


def download(c):
    """Download a component if the file does not exist; warn if too old."""
    if not os.path.isfile(c.path):
        print('downloading {}...'.format(c.name))
        raw_dl(c.dl_link, c.path)
        print('{:25} -> downloaded -> {:30}'.format(c.name, c.filename[:25]))
    if time.time() - os.stat(c.path).st_mtime > 86400*(c.days_since_update+1):
        print('WARNING: {0.name} file older than update!'.format(c))


def download_files():
    """Download files which are in config.yml, but not saved in components."""
    if not os.path.isdir('components'):
        os.mkdir('components')
    with concurrent.futures.ThreadPoolExecutor() as executor:
        executor.map(download, ALL.values(), timeout=60)


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
    @cache
    def json(self, ID):
        return requests.get(
            'http://dffd.bay12games.com/file_data/{}.json'.format(ID)).json()

    def dl_link(self, ID):
        return 'http://dffd.bay12games.com/download.php?id={}&f=b'.format(ID)

    def days_since_update(self, ID):
        return (datetime.date.today() - datetime.date.fromtimestamp(
            float(self.json(ID)['updated_timestamp']))).days


class GitHubMetadata(AbstractMetadata):
    @cache
    def json(self, repo):
        # Abstract the release/tag differences here if possible
        url = 'https://api.github.com/repos/{}/releases/latest'.format(repo)
        auth = None
        if os.path.isfile('_CRED'):
            with open('_CRED') as f:
                auth = tuple(f.read().split())
        release = requests.get(url, auth=auth).json()
        if repo == 'DFHack/dfhack':  # get a prerelease build if available
            url = 'https://api.github.com/repos/DFHack/dfhack/releases'
            release = requests.get(url, auth=auth).json()[0]

        if release.get('assets'):
            assets = sorted(release['assets'], key=lambda a: len(a['name']))
            win = [a for a in assets if 'win' in a['name'].lower()]
            win64 = [a for a in win if '64' in a['name']]
            lst = win64 if win64 else (win if win else assets)
            release['dl_link'] = lst[0]['browser_download_url']
            release['filename'] = os.path.basename(release['dl_link'])
            for key in ['author', 'body', 'assets']:
                release.pop(key)
            release['version'] = release['tag_name'].replace('\r', '')
            return release

        tags_url = 'https://api.github.com/repos/{}/tags'.format(repo)
        tags = requests.get(tags_url, auth=auth).json()
        if 'message' in tags:
            print(tags['message'])  # Probably hit API rate limit; wait an hour
        tag = tags[0]
        tag['dl_link'] = tag['zipball_url']
        tag['filename'] = '{}_{}.zip'.format(
            repo.replace('/', '_'), os.path.basename(tag['dl_link']))
        tag['published_at'] = requests.get(
            tag['commit']['url'], auth=auth).json()['commit']['author']['date']
        tag['version'] = tag['name']
        return tag

    def days_since_update(self, ID):
        return (datetime.datetime.today() - datetime.datetime.strptime(
            self.json(ID)['published_at'], '%Y-%m-%dT%H:%M:%SZ')).days


class ManualMetadata(AbstractMetadata):
    def json(self, identifier):
        with open('config.yml') as f:
            for category in yaml.safe_load(f).values():
                if identifier in category:
                    return category[identifier]

    def filename(self, identifier):
        return os.path.basename(self.dl_link(identifier))

    def days_since_update(self, ID):
        return (datetime.date.today() -
                self.json(ID).get('updated', datetime.date(2005, 1, 1))).days


_template = collections.namedtuple('Component', [
    'category', 'name', 'path',
    'filename', 'dl_link', 'version',
    'days_since_update', 'tooltip', 'page'])


def _component(data):
    """Lighter weight than a class, but still easy to access."""
    category, item = data
    with open('config.yml') as f:
        config = yaml.safe_load(f)[category][item]
    ident = item if config['host'] == 'manual' else config['ident']
    meta = {'dffd': DFFDMetadata, 'github': GitHubMetadata,
            'manual': ManualMetadata}[config['host']]()
    return _template(
        category, item, os.path.join('components', meta.filename(ident)),
        meta.filename(ident), meta.dl_link(ident), meta.version(ident),
        meta.days_since_update(ident),
        config.get('tooltip', '').replace('\n', ''),
        'http://www.bay12forums.com/smf/index.php?topic={}'.format(
            config.get('bay12', 126076)))


def df_metadata():
    """Fetch metadata about DF."""
    @cache
    def _get_df_meta(null, ident):
        """Use inner function to ensure cache key is identical across calls."""
        #pylint:disable=unused-argument
        url = 'http://bay12games.com/dwarves/dev_release.rss'
        for line in requests.get(url).text.split('\n'):
            if line.startswith('      <title>'):
                for s in ['      <title>', ' Released</title>']:
                    line = line.replace(s, '')
                day, df_version = (s.strip() for s in line.split(': DF'))
        return df_version, datetime.datetime.strptime(day, '%Y-%m-%d')
    return _get_df_meta(None, 'Dwarf Fortress')


def _component_DF():
    """DF is the sole, hard-coded special case to avoid manual management."""
    link = 'http://bay12games.com/dwarves/'
    df_version, updated = df_metadata()
    filename = 'df_{0[1]}_{0[2]}_win.zip'.format(df_version.split('.'))
    return _template(
        'files', 'Dwarf Fortress', os.path.join('components', filename),
        filename, link + filename, df_version,
        (datetime.datetime.today() - updated).days, '', link)


def get_globals():
    """Returns the dict and lists for the module variables
    ALL, FILES, GRAPHICS, and UTILITIES."""
    with open('config.yml') as ymlf:
        items = [(c, i) for c, v in yaml.safe_load(ymlf).items() for i in v]
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = executor.map(_component, items, timeout=20)
    all_comps = {r.name: r for r in results}
    all_comps['Dwarf Fortress'] = _component_DF()
    yield all_comps
    yield from [sorted({c for c in all_comps.values() if c.category == t},
                       key=lambda c: c.name)
                for t in ('files', 'graphics', 'utilities')]

if __name__ != '__main__':
    ALL, FILES, GRAPHICS, UTILITIES = get_globals()
