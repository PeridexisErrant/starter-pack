"""Handles version strings for various things."""

import yaml


with open('config.yml') as f:
    YML = yaml.safe_load(f)


def df(*, dirname=False):
    """Return the version string of Dwarf Fortress, or the dirname I use."""
    string = 'Dwarf Fortress ' if dirname else ''
    return string + YML['files']['Dwarf Fortress']['version']


def starter_pack(*, dirname=False):
    """Return the version string of my Starter Pack, or the dirname I use."""
    # TODO:  make the updater batch script compatible with this naming scheme
    string = "PeridexisErrant's Starter Pack " if dirname else ''
    return '{}{}-{}'.format(string, df(), YML['version'])
