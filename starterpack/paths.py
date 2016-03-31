"""Utility methods to get various paths.  Acts as a single source of truth."""
# pylint:disable=missing-docstring,cyclic-import

import os
import sys


# TODO:  allow setting by config file to `cross-compile'
HOST_OS = {
    'linux': 'linux',
    'win32': 'win',
    'cygwin': 'win',
    'darwin': 'osx',
    }[sys.platform]


def df_ver(as_string=True):
    """Return the current version string of Dwarf Fortress."""
    from . import component
    ver = component.ALL['Dwarf Fortress'].version
    return ver if as_string else tuple(ver.split('.')[1:])


def pack_ver():
    """Return the current version string of the created pack."""
    with open('base/changelog.txt') as f:
        ver = f.readline().strip()
    if not ver.startswith(df_ver()):
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
    # TODO:  support naming output from config file
    return dist("PeridexisErrant's Starter Pack {}.zip".format(pack_ver()))


def base(*paths):
    """Return the path to the persistent content directory."""
    return os.path.join('base', *paths)
