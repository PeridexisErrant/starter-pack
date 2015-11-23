"""Unpack downloaded files to the appropriate place.

Includes generic unzipping to a location, automatic handling of utilities
and other special categories, and individual logic for other files.

Many functions are VERY tightly coupled to the contents of config.yml
"""

import os
import shutil
import zipfile

from . import component
from . import paths


def unzip_to(filename, target_dir, *, makedirs=False):
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
    if not os.path.isdir(target_dir):
        raise FileNotFoundError('Cannot extract to missing dir: ' + target_dir)
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


def create_utilities():
    """Extract all utilities to the build/LNP/Utilities dir."""
    for d in os.listdir(paths.utilities()):
        if os.path.isdir(paths.utilities(d)):
            print('deleting', d)
            shutil.rmtree(paths.utilities(d))
    for util in (u for c, u in component.ITEMS if c == 'utilities'):
        target = paths.utilities(util)
        comp = component.Component('utilities', util)
        print('{:20}  ->  {}'.format(comp.filename[:20], target))
        unzip_to(comp.path, target, makedirs=True)
