"""Configures the extracted pack.

This includes removing duplicate or unwanted files, installing settings,
and so on.

While this involves a lot of interaction with details of the contents,
I've tried to keep it flexible enough not to break on alternative
configurations - though it might not be much use.
"""

import json
import os
import shutil

import yaml

from . import component
from . import extract
from . import paths


# General utility functions

def overwrite_dir(src, dest):
    """Copies a tree from src to dest, adding files."""
    if os.path.isdir(src):
        if not os.path.isdir(dest):
            os.makedirs(dest)
        for f in os.listdir(src):
            overwrite_dir(os.path.join(src, f), os.path.join(dest, f))
    else:
        shutil.copy(src, os.path.dirname(dest))


def rough_simplify(df_dir):
    """Remove all files except data, raw, and manifests.json"""
    for fname in os.listdir(df_dir):
        path = os.path.join(df_dir, fname)
        if os.path.isfile(path):
            if fname != 'manifest.json':
                os.remove(path)
        elif fname not in {'data', 'raw'}:
            shutil.rmtree(path)


def fixup_manifest(filename, comp, **kwargs):
    """Update manifest.json at `filename` with metadata for `comp`."""
    if not os.path.isfile(filename):
        if comp.category != 'utilities':
            print('WARNING:  no manifest for {}!'.format(comp.name))
        elif component.ALL.get('PyLNP', '').version > 'PyLNP_0.10f':
            raise DeprecationWarning('Require upstream utility manifests?')

    # Set title and other metadata from in components.yml
    manifest = {'title': comp.name,
                'needs_dfhack': comp.needs_dfhack,
                'content_version': comp.version}
    manifest.update(comp.manifest)
    # Set keyword arguments (used for utilities executable autodetection)
    manifest.update(kwargs)
    # Override autodetection with prexisting manifest fields, if any
    if os.path.isfile(filename):
        with open(filename) as f:
            manifest.update(json.load(f))
    # Warn about and discard incompatibility flag
    if manifest.get('df_max_version', '1') < paths.DF_VERSION:
        print('WARNING: overriding df_max_version {} for {}'.format(
            manifest.get('df_max_version'), comp.name))
        manifest.pop('df_max_version', None)
    # Finally, save the complete manifest
    with open(filename, 'w') as f:
        json.dump(manifest, f, indent=4)


# Configure utilities

def _soundsense_xml():
    """Check and update version strings in xml path config"""
    xmlfile = paths.utilities('Soundsense', 'configuration.xml')
    relpath = os.path.relpath(paths.df(), paths.utilities('Soundsense'))
    with open(xmlfile) as f:
        config = f.readlines()
    for n, line in enumerate(config):
        if 'gamelog.txt' in line:
            config[n] = '\t<gamelog encoding="Cp850" path="{}"/>\n'.format(
                os.path.join(relpath, 'gamelog.txt'))
        elif 'ss_fix.log' in line:
            config[n] = '\t\t<item path="{}"/>\n'.format(
                os.path.join(relpath, 'ss_fix.log'))
    with open(xmlfile, 'w') as f:
        f.writelines(config)


def _therapist_ini():
    """Ensure memory layout for Dwarf Therapist is present."""
    fname = 'v{}_graphics.ini'.format(paths.DF_VERSION)
    comp_path = os.path.join('components', fname)
    util_path = paths.utilities('Dwarf Therapist', 'share', 'memory_layouts',
                                'windows', fname)
    url = ('https://raw.githubusercontent.com/splintermind/Dwarf-Therapist'
           '/DF2016/share/memory_layouts/windows/' + fname)
    if not os.path.isfile(util_path):
        try:
            if not os.path.isfile(comp_path):
                component.raw_dl(url, comp_path)
            shutil.copy(comp_path, util_path)
        except IOError:
            print('WARNING:  Therapist memory layout unavailable!')


def create_utilities():
    """Confgure utilities metadata and check config files."""
    _soundsense_xml()
    _therapist_ini()
    for util in component.UTILITIES:
        if util.needs_dfhack and extract.DFHACK_VER is None:
            continue
        exe = []
        for _, _, files in os.walk(paths.utilities(util.name)):
            exe.extend(f for f in files if f.endswith('.exe'))
        fixup_manifest(paths.utilities(util.name, 'manifest.json'),
                       util, win_exe=sorted(exe)[0])

    if component.ALL.get('PyLNP', '').version > 'PyLNP_0.10f':
        raise DeprecationWarning('Time to remove utilities.txt code?')
        # https://bitbucket.org/Pidgeot/python-lnp/pull-requests/61
    with open(paths.utilities('utilities.txt'), 'w') as f:
        for util in component.UTILITIES:
            if util.needs_dfhack and extract.DFHACK_VER is None:
                continue
            exe, jars = [], []
            for _, _, files in os.walk(paths.utilities(util.name)):
                for fname in files:
                    if fname.endswith('.exe'):
                        exe.append(fname)
                    elif fname.endswith('.jar'):
                        jars.append(fname)
            f.write(''.join('[{}:EXCLUDE]\n'.format(j) for j in jars))
            f.write('[{}:{}:{}]\n\n'.format(
                sorted(exe)[0], util.name, util.manifest.get('tooltip', '')))


# Configure graphics packs

def _twbt_settings(pack):
    """Set TwbT-specific options for a graphics pack."""
    if not os.path.isfile(paths.df('hack', 'plugins', 'twbt.plug.dll')):
        return
    init_file = paths.graphics(pack, 'data', 'init', 'init.txt')
    with open(init_file) as f:
        init = f.readlines()
    for n, _ in enumerate(init):
        if init[n].startswith('[FONT:') and pack != 'CLA':
            init[n] = '[FONT:curses_640x300.png]\n'
        elif init[n].startswith('[FULLFONT:') and pack != 'CLA':
            init[n] = '[FULLFONT:curses_640x300.png]\n'
        elif init[n].startswith('[PRINT_MODE:'):
            init[n] = '[PRINT_MODE:TWBT]\n'
    with open(init_file, 'w') as f:
        f.writelines(init)


def _check_a_graphics_pack(pack):
    """Fix up the given graphics pack."""
    # Check that all is well...
    files = os.listdir(paths.graphics(pack))
    if not ('data' in files and 'raw' in files):
        print(pack + ' graphics pack malformed!')
    # Reduce filesize
    rough_simplify(paths.graphics(pack))
    for file in os.listdir(paths.graphics(pack, 'data', 'art')):
        if file in os.listdir(paths.lnp('tilesets')) or file.endswith('.bmp'):
            os.remove(paths.graphics(pack, 'data', 'art', file))
    if pack != 'ASCII':
        fixup_manifest(paths.graphics(pack, 'manifest.json'),
                       component.ALL[pack])
        if not component.ALL[pack].needs_dfhack:  # native TwbT support assumed
            _twbt_settings(pack)


def create_graphics():
    """Extract all graphics packs to the build/LNP/Graphics dir."""
    # Add manifest to ASCII graphics
    manifest = {"author": "ToadyOne", "content_version": paths.DF_VERSION,
                "tooltip": "Default graphics for DF, exactly as they come."}
    with open(paths.graphics('ASCII', 'manifest.json'), 'w') as f:
        json.dump(manifest, f, indent=4)
    for pack in os.listdir(paths.graphics()):
        _check_a_graphics_pack(pack)


# Configure other LNP/* parts

def build_lnp_dirs():
    """Miscellaneous cleanup and configuration; see comments."""
    # Install LNP/Extras in DF dir (DFHack init files, etc)
    overwrite_dir(paths.lnp('extras'), paths.df())

    # Create menu entry in PylNP for vanilla keybinds
    with open(paths.lnp('keybinds', 'Vanilla DF.txt'), 'w',
              encoding='cp437') as f:
        f.write('\n')

    # Add vanilla tilesets to LNP/Tilesets
    for img in {'curses_640x300', 'curses_800x600',
                'curses_square_16x16', 'mouse'}:
        shutil.copy(paths.curr_baseline('data', 'art', img + '.png'),
                    paths.lnp('tilesets'))
    # Add vanilla colourscheme to list
    shutil.copy(paths.curr_baseline('data', 'init', 'colors.txt'),
                paths.lnp('colors', 'ASCII Default.txt'))

    # Make defaults dir, pull in contents, and copy over DF folder
    # TODO:  upgrade for https://bitbucket.org/Pidgeot/python-lnp/issues/87
    default_dir = paths.lnp('defaults')
    os.makedirs(default_dir)
    shutil.copy(paths.lnp('embarks', 'default_profiles.txt'), default_dir)
    for f in {'init.txt', 'd_init.txt'}:
        shutil.copy(paths.graphics('Phoebus', 'data', 'init', f), default_dir)
    overwrite_dir(default_dir, paths.df('data', 'init'))
    os.rename(paths.df('data', 'init', 'default_profiles.txt'),
              paths.df('data', 'init', 'embark_profiles.txt'))

    # Reduce filesize of baseline
    rough_simplify(paths.curr_baseline())

    # Create new PyLNP.json
    with open(paths.base('PyLNP-json.yml')) as f:
        pylnp_conf = yaml.load(f)
    pylnp_conf['updates']['packVersion'] = paths.PACK_VERSION
    with open(paths.lnp('PyLNP.json'), 'w') as f:
        json.dump(pylnp_conf, f, indent=2)


def build_df():
    """Set up DF dir with DFHack config, install graphics, etc."""
    # 0.42.03 bug - can't save macros without this dir; breaks Quickfort
    # http://www.bay12games.com/dwarves/mantisbt/view.php?id=9398
    os.makedirs(paths.df('data', 'init', 'macros'))
    # Several utilities assume gamelog.txt exists and misbehave otherwise
    with open(paths.df('gamelog.txt'), 'w', encoding='cp437') as f:
        f.write('*** STARTING NEW GAME ***\n')

    if extract.DFHACK_VER is not None:
        os.rename(paths.df('dfhack.init-example'), paths.df('dfhack.init'))
        # Rename the example init file; disable prerelease builds
        hack = component.ALL.get('DFHack')
        if '-r' not in hack.version:
            print('DFHack is a prerelease version; disabling...')
            shutil.copy(paths.df('SDL.dll'), paths.df('SDLhack.dll'))
            shutil.copy(paths.df('SDLreal.dll'), paths.df('SDL.dll'))
    # Install Phoebus graphics by default
    pack = 'Phoebus'
    if pack in os.listdir(paths.graphics()):
        shutil.rmtree(paths.df('raw', 'graphics'))
        overwrite_dir(paths.graphics(pack), paths.df())
        with open(paths.df('raw', 'installed_raws.txt'), 'w') as f:
            txt = 'baselines/{}\ngraphics/{}\n'
            f.write(txt.format(os.path.basename(paths.curr_baseline()), pack))
    else:
        print('WARNING:  {} graphics not available to install!'.format(pack))


def main():
    """Build all components, in the required order."""
    print('\nConfiguring pack...')
    build_lnp_dirs()
    create_utilities()
    create_graphics()
    build_df()
