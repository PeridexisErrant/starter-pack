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
import datetime
import os
import yaml

import requests


def cache(method, *, saved={}, dump=False):
    """A local cache is faster, and avoids GitHub API ratelimit."""
    if not saved:
        try:
            with open('_cached.yml') as f:
                saved.update(yaml.load(f))
            print('Loaded metadata cache; delete "_cached.yml" to refresh.\n')
        except IOError:
            saved['notified'] = True
            print('No metadata cache; will download from APIs.\n')
    if saved and dump and not os.path.isfile('_cached.yml'):
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


def download_files(comps=None):
    """Download files which are in config.yml, but not saved in components."""
    if comps is None:
        comps = ALL.values()
    for c in comps:
        if os.path.isfile(c.path):
            continue
        print('downloading {}...'.format(c.name))
        buf = b''.join(requests.get(c.dl_link).iter_content(1024))
        with open(c.path, 'wb') as f:
            f.write(buf)
        print('{:25} -> downloaded -> {:30}'.format(c.name, c.filename[:25]))


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
            release['version'] = release['tag_name'].replace('\r', '')
            return release
        tags_url = 'https://api.github.com/repos/{}/tags'.format(repo)
        tags = requests.get(tags_url).json()
        if 'message' in tags:
            print(tags['message'])  # Probably hit API rate limit; wait 5
        tag = tags[0]
        tag['dl_link'] = tag['zipball_url']
        tag['filename'] = '{}_{}.zip'.format(
            repo.replace('/', '_'), os.path.basename(tag['dl_link']))
        tag['published_at'] = requests.get(
            tag['commit']['url']).json()['commit']['author']['date']
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


def _component(category, item):
    """Lighter weight than a class, but still easy to access."""
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


if __name__ != '__main__':
    with open('config.yml') as ymlf:
        _items = ((c, i) for c, v in yaml.safe_load(ymlf).items() for i in v)
        ALL = {i: _component(c, i) for c, i in _items}
    ALL['Dwarf Fortress'] = _component_DF()
    FILES = [c for c in ALL.values() if c.category == 'files']
    GRAPHICS = [c for c in ALL.values() if c.category == 'graphics']
    UTILITIES = [c for c in ALL.values() if c.category == 'utilities']
    for l in (FILES, GRAPHICS, UTILITIES):
        l.sort(key=lambda c: c.name)
