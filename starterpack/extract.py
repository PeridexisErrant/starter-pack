"""Unpack downloaded files to the appropriate place.

This module is about as generic as it can usefully be, pushing the special
cases back into build.py
"""

import os
import shutil
import zipfile

from . import component
from . import paths

DFHACK_VER = None


def unzip_to(filename, target_dir):
    """Extract the contents of the given archive to the target directory.

    - If the filename is not a zip file, copy '.exe's to target_dir.
        For other file types, print a warning (everyone uses .zip for now)
    - If the zip is all in a single compressed folder, traverse it.
        We want the target_dir to hold files, not a single subdir.
    """
    # TODO:  abstraction of get-particular-file-from-archive
    # See PyLNP, DFFD-edition Gemset, TwbT, etc.
    if not (filename.endswith('.zip') and zipfile.is_zipfile(filename)):
        raise IOError(filename + ' is not a valid .zip file.')
    print('{:20}  ->  {}'.format(os.path.basename(filename)[:20], target_dir))
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


def _extract_twbt():
    """TwbT extraction is a bit of a pain."""
    plugins = ['{}/{}.plug.dll'.format(DFHACK_VER, plug)
               for plug in ('automaterial', 'mousequery', 'resume', 'twbt')]
    done = False
    with zipfile.ZipFile(component.ALL['TwbT'].path) as zf:
        for obj, name in zip(zf.infolist(), zf.namelist()):
            if name in plugins:
                done = True
                outpath = paths.df('hack', 'plugins', os.path.basename(name))
                with open(outpath, 'wb') as out:
                    shutil.copyfileobj(zf.open(obj), out)
    if done:
        print('{:20}  ->  {}'.format(os.path.basename(
            component.ALL['TwbT'].path)[:20], os.path.dirname(outpath)))
    else:
        print('WARNING:  TwbT not installed; not compatible with DFHack.')


def extract_files():
    """Extract the miscelaneous files in components.yml"""
    for comp in component.FILES:
        if comp.name == 'DFHack':
            continue
        if comp.needs_dfhack and DFHACK_VER is None:
            print(comp.name, 'not installed - requires DFHack')
            continue
        if comp.name == 'TwbT':
            _extract_twbt()
            continue
        dest, *details = comp.extract_to.split('/')
        if not dest:
            print('No destination configured for file:', comp.name)
            continue
        # first part of extract_to is paths method, remainder is args
        unzip_to(comp.path, getattr(paths, dest)(*details))


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
