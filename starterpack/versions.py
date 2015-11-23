"""Handles version strings for various things."""

import yaml

from . import download


with open('config.yml') as f:
    YML = yaml.safe_load(f)


def df(*, dirname=False):
    string = 'Dwarf Fortress ' if dirname else ''
    return string + YML['files']['Dwarf Fortress']['version']


def starter_pack(*, dirname=False):
    # TODO:  make the updater batch script compatible with this naming scheme
    string = "PeridexisErrant's Starter Pack " if dirname else ''
    return '{}{}-{}'.format(string, df(), YML['version'])
