"""Utility methods to get various paths.  Acts as a single source of truth."""
# pylint:disable=missing-docstring,cyclic-import

import argparse
from contextlib import suppress
import os
import sys

import yaml


CONFIG = {}
with suppress(IOError):
    with open('config.yml') as ymlf:
        CONFIG = yaml.safe_load(ymlf)

parser = argparse.ArgumentParser()
parser.add_argument('--os', choices=['win', 'linux', 'osx'],
                    default=CONFIG.get('os') or {
                    'linux': 'linux',  'win32': 'win',
                    'cygwin': 'win', 'darwin': 'osx'}[sys.platform])
parser.add_argument('--bits', choices=['32', '64',],
                    default=str(CONFIG.pop('desired_bits', '64')))
parser.add_argument('--prerelease-components', action='store_true',
                    default=CONFIG.get('allow_prerelease_components', False))
parser.add_argument('--prerelease-components', action='store_true',
                    default=CONFIG.get('allow_prerelease_components', False))
parser.add_argument('--pack-release', action='store_true')
ARGS = parser.parse_args()

BITS = ARGS.bits
assert BITS in ('32', '64')

HOST_OS = ARGS.os


def df_ver(as_string=True):
    """Return the current version string of Dwarf Fortress."""
    from . import component
    ver = component.ALL['Dwarf Fortress'].version
    return ver if as_string else tuple(ver.split('.')[1:])


def pack_ver(*, warn=True):
    """Return the current version string of the created pack."""
    with open('base/changelog.txt') as f:
        ver = f.readline().strip()
    if warn and not ver.startswith(df_ver()):
        print('ERROR:  pack version must start with DF version.')
    return ver


def build(*paths):
    """Return the path to the main pack directory ('build')."""
    return os.path.join('build', *paths)


def df(*paths):
    """Return the path to the DF directory in the built pack."""
    return build('Dwarf Fortress ' + df_ver(), *paths)


def plugins(*paths):
    return df('hack', 'plugins', *paths)


def lnp(*paths):
    return build('LNP', *paths)


def utilities(*paths):
    return lnp('utilities', *paths)


def graphics(*paths):
    return lnp('graphics', *paths)


def curr_baseline(*paths):
    dname = 'df_{0[1]}_{0[2]}'.format(df_ver().split('.'))
    return lnp('baselines', dname, *paths)


def dist(*paths):
    """Return the path to the distribution dir."""
    return os.path.join('dist', *paths)


def zipped():
    """Return the path to the zipped pack to upload."""
    name = CONFIG.get('packname') or "Unknown Pack {}"
    return dist(name.format(pack_ver(warn=False)) + '.zip')


def base(*paths):
    """Return the path to the persistent content directory."""
    return os.path.join('base', *paths)


def components(*paths):
    """Return the path to the downloaded components cache dir."""
    return os.path.join('components', *paths)
