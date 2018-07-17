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
            if fname != 'manifest.json' and not fname.endswith('.init'):
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
    # overwrite metadata in order: detected, configured, in-code, upstream
    manifest = {'title': comp.name, 'needs_dfhack': comp.needs_dfhack,
                'content_version': comp.version}
    manifest.update(kwargs)
    manifest.update(comp.manifest)
    # Report if manifest in components.yml is overriding
    file_man = {}
    if os.path.isfile(filename):
        file_man = dodgy_json(filename)
    for k in comp.manifest:
        if k in file_man:
            print('WARNING:  {}: {} is provided upstream'.format(filename, k))
    manifest.update(file_man)
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
        key = paths.HOST_OS + '_exe'
        exe = manifest.get(key)
        if exe is None:
            print('WARNING: {} for {} not set!'.format(key, comp.name))
        exe = paths.utilities(comp.name, exe)
        if not os.path.isfile(exe):
            print('WARNING: {} "{}" does not exist!'.format(key, exe))
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

    if paths.HOST_OS != 'win':
        # Fix DOS line endings and make script user+group executable
        script = paths.utilities('Soundsense', 'soundSense.sh')
        with open(script) as f:
            text = f.read()
        with open(script, 'w') as f:
            f.write(text.replace('\r\n', '\n'))


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
    av = component.ALL.get('Armok Vision')
    hack = component.ALL.get('DFHack')
    if av is None or hack is None:
        return
    end = 'dll' if paths.HOST_OS == 'win' else 'so'
    if av.version.replace('v', '') < '0.17.0':
        plug = paths.utilities('Armok Vision', 'Plugins', hack.version,
                               'RemoteFortressReader.plug.' + end)
    else:
        dirname = 'v{} {}'.format(
            paths.df_ver(),
            'SDL' if paths.BITS == '32' else paths.HOST_OS + '64')
        plug = paths.utilities(
            'Armok Vision', 'Plugins', dirname, hack.version,
            'RemoteFortressReader.plug.' + end)
    if os.path.isfile(plug):
        shutil.copy2(plug, paths.plugins())
        shutil.rmtree(paths.utilities('Armok Vision', 'Plugins'))
        print('Note: installed new plugin for Armok Vision')


def _therapist_ini():
    """Ensure memory layout for Dwarf Therapist is present."""
    def teardown(message):
        print('WARNING:  {}, removing DT...'.format(message))
        therapist = component.ALL.pop('Dwarf Therapist')
        component.UTILITIES.remove(therapist)
        shutil.rmtree(paths.utilities('Dwarf Therapist'))

    if not os.path.isdir(paths.utilities('Dwarf Therapist')):
        return

    dirname = 'windows' if paths.HOST_OS == 'win' else paths.HOST_OS
    ma, mi = paths.df_ver(as_string=False)
    fname = 'v0.{}.{}_graphics_{}{}.ini'.format(
        ma, mi, paths.HOST_OS, paths.BITS)
    util_path = paths.utilities(
        'Dwarf Therapist', 'data', 'memory_layouts', dirname, fname)
    if not os.path.isfile(util_path):
        url = ('https://raw.githubusercontent.com/Dwarf-Therapist/'
               'Dwarf-Therapist/master/share/memory_layouts/{}/{}')
        comp_path = paths.components(fname)
        try:
            if not os.path.isfile(comp_path):
                component.raw_dl(url.format(dirname, fname), comp_path)
            shutil.copy(comp_path, util_path)
        except Exception:  # pylint:disable=broad-except
            teardown('no Therapist memory layout')


def _exes_for(util):
    """Find the best available match for Windows and macOS utilities."""
    win_exe, osx_exe, linux_exe = '', '', ''
    for _, dirs, files in os.walk(paths.utilities(util.name)):
        # Windows: first .exe found, first .bat otherwise
        # Linux: first .jar found, otherwise .sh
        # macOS: as for linux, but a .app directory wins
        for f in files:
            if win_exe and osx_exe and linux_exe:
                break
            if f.endswith('.exe'):
                win_exe = f
                break
            elif not win_exe and f.endswith('.bat'):
                win_exe = f
            elif f.endswith('.jar'):
                osx_exe = f
                linux_exe = f
            elif f.endswith('.sh'):
                if not osx_exe:
                    osx_exe = f
                if not linux_exe:
                    linux_exe = f
        for dname in dirs:
            if dname.endswith('.app'):
                osx_exe = dname
                break
    return {'win_exe': win_exe, 'osx_exe': osx_exe, 'linux_exe': linux_exe}


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
        if paths.HOST_OS != 'win':
            with open(paths.utilities(util.name, 'manifest.json')) as f:
                exe = json.load(f)[paths.HOST_OS + '_exe']
            path = paths.utilities(util.name, exe)
            os.chmod(path, 0o110 | os.stat(path).st_mode)


# Configure graphics packs

def _twbt_settings(pack):
    """Set TwbT-specific options for a graphics pack."""
    leave_text_tiles = ('CLA', 'DungeonSet')
    if not os.path.isfile(paths.df('hack', 'plugins', 'twbt.plug.dll')):
        return
    if component.ALL.get('TwbT').version >= 'v5.77' and paths.BITS != '64':
        raise RuntimeError('This version of TwbT does not support 32-bit.')
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
    # Copy twbt-specific graphics files into place
    for dir_, k in [('raw', 'graphics'), ('raw', 'objects'),
                    ('data', 'art'), ('data', 'init')]:
        t = paths.graphics(pack, dir_, 'twbt_' + k)
        if os.path.isdir(t):
            overwrite_dir(t, paths.graphics(pack, 'raw', k))
            shutil.rmtree(t)


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
        # If the needs_dfhack key is set for a graphics pack, assume that it
        # has native TwbT support.  Otherwise, try to patch it in...
        if not component.ALL[pack].needs_dfhack:
            _twbt_settings(pack)
    for file in os.listdir(paths.lnp('tilesets')):
        if not os.path.isfile(paths.df('data', 'art', file)):
            shutil.copy(paths.lnp('tilesets', file),
                        paths.df('data', 'art', file))


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
    pylnp_conf['updates']['dffdID'] = paths.CONFIG['dffdID']
    if not paths.ARGS.stable:
        pylnp_conf['updates']['dffdID'] = paths.CONFIG['unstable_dffdID']
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
    # Various utilities assume this dir exists, but some DF releases omit it
    os.makedirs(paths.df('data', 'init', 'macros'), exist_ok=True)
    # Several utilities assume gamelog.txt exists and misbehave otherwise
    with open(paths.df('gamelog.txt'), 'w', encoding='cp437') as f:
        f.write('*** STARTING NEW GAME ***\n')

    if 'DFHack' in component.ALL:
        for init in ('dfhack', 'onLoad'):
            os.rename(paths.df(init + '.init-example'),
                      paths.df(init + '.init'))
        with open(paths.df('dfhack.init')) as f:
            ini = f.read()
        with open(paths.df('dfhack.init'), mode='w') as f:
            f.write(ini.replace('.init-example', '.init'))
        hack = component.ALL['DFHack']
        if paths.HOST_OS == 'win':
            real_size = os.path.getsize(paths.df('SDLreal.dll'))
            shutil.copy(paths.df('SDL.dll'), paths.df('SDLhack.dll'))
            hack_size = os.path.getsize(paths.df('SDLhack.dll'))
            assert hack_size > 2 * real_size
            assert os.path.getsize(paths.df('SDL.dll')) == hack_size
            if 'alpha' in hack.version.lower():
                print('DFHack is an alpha version; disabling...')
                shutil.copy(paths.df('SDLreal.dll'), paths.df('SDL.dll'))
        # Check docs exist, and minimise size
        if os.path.isfile(paths.df('hack', 'docs', 'index.html')):
            shutil.rmtree(paths.df('hack', 'docs', '.doctrees'),
                          ignore_errors=True)
        else:
            print('WARNING: DFHack distributed without html docs.')
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
    # Set macro delay to zero, for Quickfort
    with open(paths.init('init.txt'), encoding='cp437') as f:
        init = f.read().replace('[MACRO_MS:15]', '[MACRO_MS:0]')
    with open(paths.init('init.txt'), 'w', encoding='cp437') as f:
        f.write(init)


def main():
    """Build all components, in the required order."""
    print('\nConfiguring pack...')
    build_lnp_dirs()
    create_utilities()
    create_graphics()
    build_df()
