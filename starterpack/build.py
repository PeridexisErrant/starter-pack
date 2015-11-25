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
    print('{:20}  ->  {}'.format(filename[:20], target_dir))
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


def rough_simplify(df_dir):
    """Remove all files except data, raw, and manifests.json"""
    for fname in os.listdir(df_dir):
        path = os.path.join(df_dir, fname)
        if os.path.isfile(path):
            if fname != 'manifest.json':
                os.remove(path)
        elif fname not in {'data', 'raw'}:
            shutil.rmtree(path)


def _create_lnp_subdir(kind):
    """Extract all of somethine to the build/LNP/something dir."""
    for comp in (c for c in component.COMPONENTS if c.category == kind):
        target = paths.lnp(kind, comp.name)
        if os.path.isdir(target):
            print(target, 'already exists! skipping...')
            continue
        unzip_to(comp.path, target)


def create_utilities():
    """Extract all utilities to the build/LNP/Utilities dir."""
    _create_lnp_subdir('utilities')
    # TODO: generate utilities.txt


def create_graphics():
    """Extract all graphics packs to the build/LNP/Graphics dir."""
    _create_lnp_subdir('graphics')
    unzip_to(paths.component_by_name('Dwarf Fortress'),
             paths.graphics('ASCII'))
    # Only keep the 24px edition of Gemset
    gemset = glob.glob(paths.graphics('Gemset', '*_24px'))[0]
    shutil.move(gemset, paths.graphics('_temp'))
    shutil.rmtree(paths.graphics('Gemset'))
    shutil.move(paths.graphics('_temp'), paths.graphics('Gemset'))
    # Reduce filesize of graphics packs
    packs = os.listdir(paths.graphics())
    for pack in packs:
        rough_simplify(paths.graphics(pack))


def create_df_dir():
    """Create the Dwarf Fortress directory, with DFHack and other content."""
    # Extract the items below
    items = ['Dwarf Fortress', 'DFHack', 'Stocksettings']
    destinations = [paths.df(), paths.df(), paths.df('stocksettings')]
    for item, path in zip(items, destinations):
        comp = component.Component('files', item)
        unzip_to(comp.path, path)
    # Rename the example init file
    os.rename(paths.df('dfhack.init-example'), paths.df('dfhack.init'))
    # install TwbT
    plugins = ['{}/{}.plug.dll'.format(component.ALL['DFHack'].version, plug)
               for plug in ('automaterial', 'mousequery', 'resume', 'twbt')]
    with zipfile.ZipFile(component.ALL['TwbT'].path) as zf:
        for obj, name in zip(zf.infolist(), zf.namelist()):
            if name in plugins:
                outpath = paths.df('hack', 'plugins', os.path.basename(name))
                with open(outpath, 'wb') as out:
                    shutil.copyfileobj(zf.open(obj), out)


def create_baselines():
    """Extract the data and raw dirs of vanilla DF to LNP/Baselines."""
    base_dir = 'df_{0[1]}_{0[2]}'.format(paths.DF_VERSION.split('.'))
    unzip_to(paths.component_by_name('Dwarf Fortress'),
             paths.lnp('baselines', base_dir))
    rough_simplify(paths.lnp('baselines', base_dir))


def setup_pylnp():
    """Extract PyLNP and copy PyLNP.json from ./base"""
    unzip_to(component.ALL['PyLNP'].path, paths.build())
    os.rename(paths.build('PyLNP.exe'),
              paths.build('Starter Pack Launcher (PyLNP).exe'))
    os.remove(paths.build('PyLNP.json'))
    with open(paths.base('PyLNP.json')) as f:
        pylnp_conf = json.load(f)
    pylnp_conf['updates']['packVersion'] = paths.PACK_VERSION
    with open(paths.lnp('PyLNP.json'), 'w') as f:
        json.dump(pylnp_conf, f, indent=2)


def install_misc_files():
    """Install the various files that need to be added after the fact."""
    # XML file for PerfectWorld
    unzip_to(component.ALL['PerfectWorld XML'].path,
             paths.utilities('PerfectWorld'))
    # Quickfort blueprints
    unzip_to(component.ALL['Quickfort Blueprints'].path,
             paths.utilities('Quickfort', 'blueprints'))


def build_all():
    """Build all components, in the required order."""
    create_df_dir()
    create_utilities()
    create_graphics()
    create_baselines()
    setup_pylnp()
    install_misc_files()


# This block just checks that each 'file' is handled by some function.
# It does not execute them; just register that they exist.
funcs = {
    'Dwarf Fortress': create_df_dir,
    'DFHack': create_df_dir,
    'PerfectWorld XML': install_misc_files,
    'PyLNP': setup_pylnp,
    'Quickfort Blueprints': install_misc_files,
    'Stocksettings': create_df_dir,
    'TwbT': create_df_dir,
    }

for compon in component.FILES:
    if compon.name not in funcs:
        print('WARNING: {} does not have a registered installer.')
