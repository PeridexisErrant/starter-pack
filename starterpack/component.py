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
import re
import time

import requests
import yaml

from . import metadata_api, paths


def report():
    print('Component:            Age:   Version:       Filename:')
    for comp in sorted(ALL.values(), key=lambda c: c.days_since_update):
        print(' {:22}{:4}   {:15}{:30}'.format(
            comp.name[:19], comp.days_since_update,
            comp.version, comp.filename[:30]))
    metadata_api.cache(dump=True)


def raw_dl(url, path):
    """Save url contents to a file."""
    req = requests.get(url)
    req.raise_for_status()
    with open(path, 'wb') as f:
        f.write(b''.join(req.iter_content(1024)))


def download(c):
    """Download a component if the file does not exist; warn if too old."""
    if os.path.isfile(c.path):
        file_age = (time.time() - os.stat(c.path).st_mtime) // (60 * 60 * 24)
        if file_age > c.days_since_update:
            print('file for {} may be for old version'.format(c.name))
            os.remove(c.path)
    if not os.path.isfile(c.path):
        print('downloading {}...'.format(c.name))
        raw_dl(c.dl_link, c.path)
        print('{:25} -> downloaded -> {:30}'.format(c.name, c.filename[:25]))


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
    'page',
    'needs_dfhack',
    'extract_to',
    'manifest',
    ])


class Hashabledict(dict):
    def __hash__(self):
        return hash(frozenset(self))


def _component(data):
    """Lighter weight than a class, but still easy to access."""
    category, item, config = data
    ident = item if config['host'] == 'manual' else config['ident']
    meta = metadata_api.METADATA_TYPES[config['host']]()
    forum_url = 'http://www.bay12forums.com/smf/index.php?topic={}'
    try:
        return _template(
            category,
            item,
            os.path.join('components', meta.filename(ident)),
            meta.filename(ident),
            meta.dl_link(ident),
            meta.version(ident),
            meta.days_since_update(ident),
            forum_url.format(config['bay12']),
            config.get('needs_dfhack', False),
            config.get('extract_to', ''),
            Hashabledict(config.get('manifest', {})),
            )
    except Exception:
        print('ERROR: in {}, check release exists'.format(ident))


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
    all_comps = {r.name: r for r in results if r}
    # optionally force DFHack-compatible DF version
    if paths.CONFIG.get('force_dfhack_compatible') and 'DFHack' in all_comps:
        target_ver = all_comps['DFHack'].version.replace('v', '').split('-')[0]
        df_ver = all_comps['Dwarf Fortress'].version
        if target_ver != df_ver:
            if re.match(r'0\.\d\d\.\d\d', target_ver):
                if df_ver.split('.')[1] != target_ver.split('.')[1]:
                    print('WARNING: forcing major version for DFHack compat.')
                all_comps['Dwarf Fortress'] = \
                    all_comps['Dwarf Fortress']._replace(version=target_ver)
            else:
                print('Cannot force invalid DF version ' + target_ver)
    yield all_comps
    for t in ('files', 'graphics', 'utilities'):
        yield sorted({c for c in all_comps.values() if c.category == t},
                     key=lambda c: c.name)


def main():
    report()
    download_files()


if __name__ != '__main__':
    ALL, FILES, GRAPHICS, UTILITIES = get_globals()
