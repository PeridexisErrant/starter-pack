"""Unpack downloaded files to the appropriate place.

Includes generic unzipping to a location, automatic handling of utilities
and other special categories, and individual logic for other files.

Many functions are VERY tightly coupled to the contents of config.yml
"""

import glob
import json
import os
import shutil
import zipfile

from . import component
from . import paths
from . import versions


def overwrite_dir(src, dest):
    """Copies a tree from src to dest, adding files."""
    if os.path.isdir(src):
        if not os.path.isdir(dest):
            os.makedirs(dest)
        for f in os.listdir(src):
            overwrite_dir(os.path.join(src, f), os.path.join(dest, f))
    else:
        shutil.copy(src, os.path.dirname(dest))


def unzip_to(filename, target_dir, *, makedirs=True):
    """Extract the contents of the given archive to the target directory.

    - If the filename is not a zip file, copy '.exe's to target_dir.
        For other file types, print a warning (everyone uses .zip for now)
    - If the zip is all in a single compressed folder, traverse it.
        We want the target_dir to hold files, not a single subdir.
    """
    if makedirs:
        try:
            os.makedirs(target_dir)
        except FileExistsError:
            pass
    if not filename.endswith('.zip'):
        if filename.endswith('.exe'):
            # Rare utilities, basically just Dorven Realms
            shutil.copy(filename, target_dir)
            return
        raise ValueError('Only .zip and .exe files are handled by unzip_to()')
    if not zipfile.is_zipfile(filename):
        raise ValueError(filename + ' is not a valid .zip file.')

    with zipfile.ZipFile(filename) as zf:
        contents = [a for a in zip(zf.infolist(), zf.namelist())
                    if not a[1].endswith('/')]
        while len(set(n.partition('/')[0] for o, n in contents)) == 1:
            if len(contents) == 1:
                break
            contents = [(o, n.partition('/')[-1]) for o, n in contents]
        for obj, name in contents:
            outfile = os.path.join(target_dir, name)
            if not os.path.isdir(os.path.dirname(outfile)):
                os.makedirs(os.path.dirname(outfile))
            with open(outfile, 'wb') as out:
                shutil.copyfileobj(zf.open(obj), out)


def _create_lnp_subdir(kind):
    """Extract all of somethine to the build/LNP/something dir."""
    for comp in (c for c in component.COMPONENTS if c.category == kind):
        target = paths.lnp(kind, comp.name)
        if os.path.isdir(target):
            print(target, 'already exists! skipping...')
            continue
        print('{:20}  ->  {}'.format(comp.filename[:20], target))
        unzip_to(comp.path, target)


def create_utilities():
    """Extract all utilities to the build/LNP/Utilities dir."""
    _create_lnp_subdir('utilities')
    # TODO: generate utilities.txt


def create_graphics():
    """Extract all graphics packs to the build/LNP/Graphics dir."""
    _create_lnp_subdir('graphics')
    # TODO: create ASCII graphics from DF release, instead of downloading?
    # TODO: simplify graphics packs?
    # TODO: fix Gemset (one version on each side of a fork)


def create_df_dir():
    """Create the Dwarf Fortress directory, with DFHack and other content."""
    items = ['Dwarf Fortress', 'DFHack', 'Stocksettings']
    destinations = [paths.df(), paths.df(), paths.df('stocksettings')]
    for item, path in zip(items, destinations):
        comp = component.Component('files', item)
        unzip_to(comp.path, path)
    os.rename(paths.df('dfhack.init-example'), paths.df('dfhack.init'))
    for fname in glob.glob(paths.base('*.init')):
        shutil.copy(fname, paths.df())


def pylnp_config():
    """Create LNP/PyLNP.json with correct pack version string."""
    with open(paths.base('PyLNP.json')) as f:
        pylnp_conf = json.load(f)
    pylnp_conf['updates']['packVersion'] = versions.starter_pack()
    with open(paths.lnp('PyLNP.json'), 'w') as f:
        json.dump(pylnp_conf, f, indent=2)


