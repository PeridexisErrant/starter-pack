"""Utility methods to get various paths.  Acts as a single source of truth."""
#pylint:disable=missing-docstring

import os

from . import component


DF_VERSION = component.df_metadata()[0]
with open('base/changelog.txt') as f:
    PACK_VERSION = f.readline().strip()
if not PACK_VERSION.startswith(DF_VERSION):
    raise ValueError('Error:  pack version must start with DF version.')

def build(*paths):
    """Return the path to the main pack directory ('build')."""
    return os.path.join('build', *paths)

def df(*paths):
    """Return the path to the DF directory in the built pack."""
    return build('Dwarf Fortress ' + DF_VERSION, *paths)

def lnp(*paths):
    return build('LNP', *paths)

def utilities(*paths):
    return lnp('utilities', *paths)

def graphics(*paths):
    return lnp('graphics', *paths)

def curr_baseline(*paths):
    dname = 'df_{0[1]}_{0[2]}'.format(DF_VERSION.split('.'))
    return lnp('baselines', dname, *paths)


def dist(*paths):
    """Return the path to the distribution dir."""
    return os.path.join('dist', *paths)

def zipped():
    """Return the path to the zipped pack to upload."""
    return dist("PeridexisErrant's Starter Pack {}.zip".format(PACK_VERSION))


def base(*paths):
    """Return the path to the main pack directory ('build')."""
    return os.path.join('base', *paths)
