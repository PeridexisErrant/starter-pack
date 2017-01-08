"""Configures the extracted pack.

This includes removing duplicate or unwanted files, installing settings,
and so on.

While this involves a lot of interaction with details of the contents,
I've tried to keep it flexible enough not to break on alternative
configurations - though it might not be much use.
"""

import glob
import json
import os
import shutil

import yaml

from . import component
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


def dodgy_json(filename):
    """Read json from a file, even if it's slightly invalid..."""
    with open(filename) as f:
        txt = f.read()
        return json.loads(txt[txt.find('{'):])


def fixup_manifest(filename, comp, **kwargs):
    """Update manifest.json at `filename` with metadata for `comp`."""
    file_man = {}
    if os.path.isfile(filename):
        file_man.update(dodgy_json(filename))
    # overwrite metadata in order: detected, configured, in-code, upstream
    manifest = {'title': comp.name, 'needs_dfhack': comp.needs_dfhack,
                'content_version': comp.version,
                **kwargs, **comp.manifest, **file_man}
    # Report if manifest in components.yml is overriding
    for k in comp.manifest:
        if k in file_man:
            print('WARNING:  {}: {} is provided upstream'.format(filename, k))
    # Warn about and discard incompatibility flag
    if (manifest.get('df_max_version') or '0') > paths.df_ver():
        print('WARNING: overriding df_min_version {} for {}'.format(
            manifest.get('df_min_version'), comp.name))
        manifest.pop('df_min_version', None)
    if (manifest.get('df_max_version') or '1') < paths.df_ver():
        print('WARNING: overriding df_max_version {} for {}'.format(
            manifest.get('df_max_version'), comp.name))
        manifest.pop('df_max_version', None)
    # Warn for missing fields
    if 'tooltip' not in manifest:
        print('WARNING:  no tooltip in ' + filename)
    else:
        manifest['tooltip'] = manifest['tooltip'].strip()
    if comp in component.UTILITIES:
        for _os in ('win', 'osx', 'linux'):
            if paths.HOST_OS == _os and not manifest[_os + '_exe']:
                print('WARNING: {}_exe for {} not set!'.format(_os, comp.name))
    # Save if manifest is not same as on disk
    if manifest != file_man:
        with open(filename, 'w') as f:
            json.dump({k: v for k, v in manifest.items() if v}, f, indent=4)


# Configure utilities

def _soundsense_xml():
    """Check and update version strings in xml path config"""
    xmlfile = paths.utilities('Soundsense', 'configuration.xml')
    if not os.path.isfile(xmlfile):
        return
    relpath = os.path.relpath(paths.df(), paths.utilities('Soundsense'))
    with open(xmlfile) as f:
        config = f.readlines()
    with open(xmlfile, 'w') as f:
        for line in config:
            if 'gamelog.txt' in line:
                f.write(line.replace('..', relpath))
            else:
                f.write(line)

    with open(os.path.join(paths.df(), 'ss_fix.log'), 'w') as f:
        f.write('\n')
    if component.ALL['Soundsense'].version != '2016-1':
        raise DeprecationWarning('Do you still need the empty "ss_fix.log" ?')


def _soundCenSe_config():
    """Check and update version strings in xml path config"""
    jsonpath = paths.utilities('SoundCenSe', 'Configuration.json')
    if not os.path.isfile(jsonpath):
        return
    config = dodgy_json(jsonpath)
    config['gamelogPath'] = os.path.relpath(
        paths.df(), paths.utilities('SoundCenSe'))
    if os.path.isdir(paths.utilities('Soundsense', 'packs')):
        config['soundpacksPath'] = '../Soundsense/packs/'
    with open(jsonpath, 'w') as f:
        json.dump(config, f, indent=4)


def _armok_vision_plugin():
    """Copy the new plugin into place for Armok Vision, if applicable."""
    hack = component.ALL.get('DFHack')
    if hack is None:
        return
    plug = paths.utilities('Armok Vision', 'Plugins', hack.version,
                           'RemoteFortressReader.plug.dll')
    if os.path.isfile(plug):
        shutil.copy2(plug, paths.plugins())
        shutil.rmtree(paths.utilities('Armok Vision', 'Plugins'))


def _therapist_ini():
    """Ensure memory layout for Dwarf Therapist is present."""
    if 'Dwarf Therapist' in component.ALL and \
            component.ALL['Dwarf Therapist'].version != 'v37.0.0':
        raise DeprecationWarning('Need to handle 64-bit therapist.ini')
    if not os.path.isdir(paths.utilities('Dwarf Therapist')):
        return
    dirname = 'windows' if paths.HOST_OS == 'win' else paths.HOST_OS
    fname = {
        'win': 'v0.{}.{}_graphics.ini',
        'osx': 'v0.{}.{}_osx.ini',
        'linux': 'v0{}.{}.ini'
        }[paths.HOST_OS].format(*paths.df_ver(as_string=False))
    util_path = paths.utilities(
        'Dwarf Therapist', 'share', 'memory_layouts', dirname, fname)
    if not os.path.isfile(util_path):
        url = ('https://raw.githubusercontent.com/splintermind/'
               'Dwarf-Therapist/DF2016/share/memory_layouts/{}/{}')
        comp_path = os.path.join('components', fname)
        try:
            if not os.path.isfile(comp_path):
                component.raw_dl(url.format(dirname, fname), comp_path)
            shutil.copy(comp_path, util_path)
        except Exception:  # pylint:disable=broad-except
            print('WARNING:  no Therapist memory layout, removing DT...')
            therapist = component.ALL.pop('Dwarf Therapist')
            component.UTILITIES.remove(therapist)
            shutil.rmtree(paths.utilities('Dwarf Therapist'))


def _exes_for(util):
    """Find the best available match for Windows and OSX utilities."""
    win_exe, osx_exe = '', ''
    for _, dirs, files in os.walk(paths.utilities(util.name)):
        for f in files:  # Windows: first .exe found, first .bat otherwise
            if f.endswith('.exe'):
                win_exe = f
                break
            elif not win_exe and f.endswith('.bat'):
                win_exe = f
        for f in files:  # OSX: first .jar found, otherwise .sh
            if f.endswith('.jar'):
                osx_exe = f
                break
            elif not osx_exe and f.endswith('.sh'):
                osx_exe = f
        for dname in dirs:   # But on OSX we prefer .app dirs above any file
            if dname.endswith('.app'):
                osx_exe = dname
                break
    return {'win_exe': win_exe, 'osx_exe': osx_exe, 'linux_exe': ''}


def create_utilities():
    """Confgure utilities metadata and check config files."""
    # Detailed checks for complicated config
    _soundsense_xml()
    _soundCenSe_config()
    _therapist_ini()
    _armok_vision_plugin()
    # Need file extension for association for readme-opener
    for readme in glob.glob(paths.utilities('*', 'README')):
        os.rename(readme, readme + '.txt')
    # Set up manifests for all utilities
    for util in component.UTILITIES:
        fixup_manifest(paths.utilities(util.name, 'manifest.json'),
                       util, **_exes_for(util))


# Configure graphics packs

def _twbt_settings(pack):
    """Set TwbT-specific options for a graphics pack."""
    leave_text_tiles = ('CLA', 'DungeonSet')
    if not os.path.isfile(paths.df('hack', 'plugins', 'twbt.plug.dll')):
        return
    init_file = paths.graphics(pack, 'data', 'init', 'init.txt')
    with open(init_file) as f:
        init = f.readlines()
    for n, _ in enumerate(init):
        if init[n].startswith('[FONT:') and pack not in leave_text_tiles:
            init[n] = '[FONT:curses_640x300.png]\n'
        elif init[n].startswith('[FULLFONT:') and pack not in leave_text_tiles:
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
    manifest = {"author": "ToadyOne", "content_version": paths.df_ver(),
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
                'curses_square_16x16'}:
        shutil.copy(paths.curr_baseline('data', 'art', img + '.png'),
                    paths.lnp('tilesets'))
    # Add vanilla colourscheme to list
    shutil.copy(paths.curr_baseline('data', 'init', 'colors.txt'),
                paths.lnp('colors', 'ASCII Default.txt'))

    # Make defaults dir, pull in contents, and copy over DF folder
    default_dir = paths.lnp('defaults')
    os.makedirs(default_dir)
    shutil.copy(paths.lnp('embarks', 'default_profiles.txt'), default_dir)
    pack = paths.CONFIG.get('default_graphics')
    if pack:
        for f in {'init.txt', 'd_init.txt'}:
            shutil.copy(paths.graphics(pack, 'data', 'init', f), default_dir)
    # TODO:  only change graphics settings... via PyLNP??
    overwrite_dir(default_dir, paths.df('data', 'init'))
    os.rename(paths.df('data', 'init', 'default_profiles.txt'),
              paths.df('data', 'init', 'embark_profiles.txt'))

    # Reduce filesize of baseline
    rough_simplify(paths.curr_baseline())

    # Create new PyLNP.json
    with open(paths.base('PyLNP-json.yml')) as f:
        pylnp_conf = yaml.load(f)
    pylnp_conf['updates']['packVersion'] = paths.pack_ver()
    for hack in pylnp_conf['dfhack'].values():
        # remove trailing newline from multiline tooltips
        hack['tooltip'] = hack['tooltip'].strip()
    with open(paths.lnp('PyLNP.json'), 'w') as f:
        json.dump(pylnp_conf, f, indent=2)
    # Create init files with any DFHack options with enabled=True
    for init_file in ('dfhack', 'onLoad', 'onMapLoad'):
        lines = [h['command'] for h in pylnp_conf['dfhack'].values()
                 if h.get('enabled') and h.get('file', 'dfhack') == init_file]
        if lines:
            with open(paths.df(init_file + '_PyLNP.init'), 'w') as f:
                f.write('\n'.join(lines))


def build_df():
    """Set up DF dir with DFHack config, install graphics, etc."""
    # Several utilities assume gamelog.txt exists and misbehave otherwise
    with open(paths.df('gamelog.txt'), 'w', encoding='cp437') as f:
        f.write('*** STARTING NEW GAME ***\n')

    if 'DFHack' in component.ALL:
        os.rename(paths.df('dfhack.init-example'), paths.df('dfhack.init'))
        # Rename the example init file; disable prerelease builds
        hack = component.ALL.get('DFHack')
        if paths.HOST_OS == 'win' and '-r' not in hack.version:
            print('DFHack is a prerelease version; disabling...')
            shutil.copy(paths.df('SDL.dll'), paths.df('SDLhack.dll'))
            shutil.copy(paths.df('SDLreal.dll'), paths.df('SDL.dll'))
        # Check docs exist, and minimise size
        if os.path.isfile(paths.df('hack', 'docs', 'index.html')):
            shutil.rmtree(paths.df('hack', 'docs', '.doctrees'),
                          ignore_errors=True)
        else:
            print('WARNING: DFHack distributed without html docs.')
        if hack.version >= '0.43.05-r0' or \
                component.ALL.get('TwbT').version > 'v5.70':
            # No good way to check, so it just goes here...
            # See https://github.com/DFHack/dfhack/issues/981
            raise DeprecationWarning('Does TwbT still supply other plugins?')
    # Install Phoebus graphics by default
    pack = paths.CONFIG.get('default_graphics')
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
