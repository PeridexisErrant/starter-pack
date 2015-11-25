"""Utility methods to get various paths.  Acts as a single source of truth."""
#pylint:disable=missing-docstring

import os
import yaml

from .component import ALL


with open('config.yml') as f:
    __YML = yaml.safe_load(f)
    DF_VERSION = __YML['files']['Dwarf Fortress']['version']
    PACK_VERSION = DF_VERSION + '-' + __YML['version']


def build(*paths):
    """Return the path to the main pack directory ('build')."""
    return os.path.join('build', *paths)

def df(*paths):
    """Return the path to the DF directory in the built pack."""
    return build('Dwarf Fortress ' + DF_VERSION, *paths)

def lnp(*paths):
    return build('LNP', *paths)

def utilities(*paths):
    return lnp('Utilities', *paths)

def graphics(*paths):
    return lnp('Graphics', *paths)


def dist(*paths):
    """Return the path to the distribution dir."""
    return os.path.join('dist', *paths)

def zipped():
    """Return the path to the zipped pack to upload."""
    return dist("PeridexisErrant's Starter Pack {}.zip".format(PACK_VERSION))


def component(*paths):
    """Return the path where downloaded components are stored."""
    return os.path.join('components', *paths)

def component_by_name(name):
    """Return the path to a downloaded component, by configured name."""
    return ALL[name].path


def base(*paths):
    """Return the path to the main pack directory ('build')."""
    return os.path.join('base', *paths)
