"""Provides abstractions over metadata storage and downloading.

 - Download metadata from file hosts, or open local cache
 - Download any missing files
 - Provide a common 'Component' object with various config methods

Any modules that use this data should just access the dict ALL (bottom).
"""
# pylint:disable=missing-docstring

import collections
import concurrent.futures
import os
import time

import requests
import yaml

from . import metadata_api


def report():
    print('Component:            Age:   Version:       Filename:')
    for comp in sorted(ALL.values(), key=lambda c: c.days_since_update):
        print(' {:22}{:4}   {:15}{:30}'.format(
            comp.name[:19], comp.days_since_update,
            comp.version, comp.filename[:30]))
    metadata_api.cache(lambda s, x: None, dump=True)


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


_template = collections.namedtuple('Component', [
    'category',
    'name',
    'path',
    'filename',
    'dl_link',
    'version',
    'days_since_update',
    'tooltip',
    'page',
    'needs_dfhack',
    'extract_to',
    ])


def _component(data):
    """Lighter weight than a class, but still easy to access."""
    category, item, config = data
    ident = item if config['host'] == 'manual' else config['ident']
    meta = metadata_api.METADATA_TYPES[config['host']]()
    forum_url = 'http://www.bay12forums.com/smf/index.php?topic={}'
    return _template(
        category,
        item,
        os.path.join('components', meta.filename(ident)),
        meta.filename(ident),
        meta.dl_link(ident),
        meta.version(ident),
        meta.days_since_update(ident),
        config.get('tooltip', '').replace('\n', ' '),
        forum_url.format(config['bay12']),
        config.get('needs_dfhack', False),
        config.get('extract_to', ''),
        )


def get_globals():
    """Returns the dict and lists for the module variables
    ALL, FILES, GRAPHICS, and UTILITIES."""
    with open('components.yml') as ymlf:
        config = yaml.safe_load(ymlf)
        config['files']['Dwarf Fortress'] = {
            'ident': 'Dwarf Fortress', 'host': 'special', 'bay12': '&board=10'}
    items = [(c, i, config[c][i]) for c, v in config.items() for i in v]
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = executor.map(_component, items, timeout=20)
    all_comps = {r.name: r for r in results}
    yield all_comps
    for t in ('files', 'graphics', 'utilities'):
        yield sorted({c for c in all_comps.values() if c.category == t},
                     key=lambda c: c.name)


def main():
    report()
    download_files()


if __name__ != '__main__':
    ALL, FILES, GRAPHICS, UTILITIES = get_globals()
