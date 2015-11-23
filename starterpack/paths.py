"""Utility methods to get various paths.  Acts as a single source of truth."""

import os

from . import versions


def build(*paths):
    """Return the path to the main pack directory ('build')."""
    return os.path.join('build', *paths)

def df(*paths):
    """Return the path to the DF directory in the built pack."""
    return build(versions.df(dirname=True), *paths)

def lnp(*paths):
    return build('LNP', *paths)

def utilities(*paths):
    return lnp('Utilities', *paths)


def dist(*paths):
    """Return the path to the distribution dir."""
    return os.path.join('dist', *paths)

def zipped():
    """Return the path to the zipped pack to upload."""
    return dist(versions.starter_pack(dirname=True))


def component(*paths):
    """Return the path where downloaded components are stored."""
    return os.path.join('components', *paths)


def base(*paths):
    """Return the path to the main pack directory ('build')."""
    return os.path.join('base', *paths)
