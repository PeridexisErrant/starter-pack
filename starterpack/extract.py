"""Unpack downloaded files to the appropriate place.

This module is about as generic as it can usefully be, pushing the special
cases back into build.py
"""

import os
import shutil
import tarfile
import zipfile

from . import component
from . import paths

DFHACK_VER = None


def unzip_to(filename, target_dir=None, path_pairs=None):
    """Extract the contents of the given archive to the target directory.

    In 'target_dir' mode, extracts the least-nested contents to the target
    directory.  This makes a zip-of-one-dir equivalent to zip-of-several-files.

    In 'path_pairs' mode, the argument should be a sequence of paths.
    The file at the first path within the zip is written at the second path.
    """
    assert bool(target_dir) != bool(path_pairs), 'Choose one unzip mode!'
    iszip = filename.endswith('.zip') and zipfile.is_zipfile(filename)
    istar = filename.endswith('.tar.bz2') and tarfile.is_tarfile(filename)
    if iszip is istar is False:
        raise IOError(filename + ' is not a valid archive file.')

    if istar:
        raise NotImplementedError('.tar.* support coming soon!  (ie not yet)')

    out = target_dir or os.path.commonpath([p[1] for p in path_pairs])
    print('{:20}  ->  {}'.format(os.path.basename(filename)[:20], out))

    def _extract(in_obj, outpath, af):
        os.makedirs(os.path.dirname(outpath), exist_ok=True)
        if isinstance(af, zipfile.ZipFile):
            with open(outpath, 'wb') as out:
                shutil.copyfileobj(af.open(in_obj), out)
        else:
            af.extractall(os.path.dirname(outpath), members=[in_obj])

    Archive = zipfile.ZipFile if iszip else tarfile.TarFile
    with Archive(filename, mode=('r' if iszip else 'r:bz2')) as af:
        names, members = (af.namelist, af.infolist) if iszip \
            else (af.getnames, af.getmembers)
        files = {name: obj for name, obj in zip(names(), members())
                 if not name.endswith('/')}
        if path_pairs is not None:
            for inpath, outpath in path_pairs:
                if inpath in files:
                    _extract(files[inpath], outpath, af)
                else:
                    print('WARNING:  {} not in {}'.format(
                        inpath, os.path.basename(filename)))
        else:
            prefix = os.path.commonpath(list(files)) if len(files) > 1 else ''
            for name in files:
                out = os.path.join(target_dir, os.path.relpath(name, prefix))
                _extract(files[name], out, af)


def extract_df():
    """Extract Dwarf Fortress, and DFHack if available and compatible."""
    # A DF dir for the main install, for baselines, and for ASCII graphics
    for p in (paths.df(), paths.curr_baseline(), paths.graphics('ASCII')):
        unzip_to(component.ALL['Dwarf Fortress'].path, p)

    hack = component.ALL.get('DFHack')
    if not hack:
        print('WARNING:  DFHack not in config, will not be installed.')
    elif paths.DF_VERSION not in hack.version:
        print('Incompatible DF, DFHack versions!  Aborting DFHack install...')
    else:
        unzip_to(hack.path, paths.df())
        return hack.version.replace('v', '')


def extract_files():
    """Extract the miscelaneous files in components.yml"""
    for comp in component.FILES:
        if comp.name in ('Dwarf Fortress', 'DFHack'):
            continue
        if comp.needs_dfhack and DFHACK_VER is None:
            print(comp.name, 'not installed - requires DFHack')
            continue
        if ':' not in comp.extract_to:
            # first part of extract_to is paths method, remainder is args
            dest, *details = comp.extract_to.split('/')
            unzip_to(comp.path, getattr(paths, dest)(*details))
        else:
            # using the path_pairs option; extract pairs from string (hashable)
            pairs = []
            for pair in comp.extract_to.strip().split('\n'):
                src, to = pair.split(':')
                dest, *details = to.split('/')
                # Note: can add format variables here as needed
                src = src.format(DFHACK_VER=DFHACK_VER)
                pairs.append([src, getattr(paths, dest)(*details)])
            unzip_to(comp.path, path_pairs=pairs)


def extract_utilities():
    """Extract the utilties in components.yml"""
    for comp in component.UTILITIES:
        if comp.needs_dfhack and DFHACK_VER is None:
            print(comp.name, 'not installed - requires DFHack')
            continue
        targetdir = paths.lnp(comp.category, comp.name)
        try:
            unzip_to(comp.path, targetdir)
        except IOError:
            if not os.path.isdir(targetdir):
                os.makedirs(targetdir)
            shutil.copy(comp.path, targetdir)


def extract_graphics():
    """Extract the graphics in components.yml"""
    for comp in component.GRAPHICS:
        if comp.needs_dfhack and DFHACK_VER is None:
            print(comp.name, 'not installed - requires DFHack')
            continue
        unzip_to(comp.path, paths.lnp(comp.category, comp.name))


def add_lnp_dirs():
    """Install the LNP subdirs that I can't create automatically."""
    # Add content from the 'base' collection
    # TODO:  use subset of https://github.com/Lazy-Newb-Pack/LNP-shared-core
    for d in ('colors', 'embarks', 'extras', 'keybinds', 'tilesets'):
        shutil.copytree(paths.base(d), paths.lnp(d))


def main():
    """Extract all components, in the required order."""
    print('\nExtracting components...')
    if os.path.isdir('build'):
        shutil.rmtree('build')
    global DFHACK_VER  # pylint:disable=global-statement
    DFHACK_VER = extract_df()
    extract_utilities()
    extract_graphics()
    extract_files()
    add_lnp_dirs()
