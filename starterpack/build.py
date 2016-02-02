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

import yaml

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


def unzip_to(filename, target_dir):
    """Extract the contents of the given archive to the target directory.

    - If the filename is not a zip file, copy '.exe's to target_dir.
        For other file types, print a warning (everyone uses .zip for now)
    - If the zip is all in a single compressed folder, traverse it.
        We want the target_dir to hold files, not a single subdir.
    """
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


def rough_simplify(df_dir):
    """Remove all files except data, raw, and manifests.json"""
    for fname in os.listdir(df_dir):
        path = os.path.join(df_dir, fname)
        if os.path.isfile(path):
            if fname != 'manifest.json':
                os.remove(path)
        elif fname not in {'data', 'raw'}:
            shutil.rmtree(path)


def install_lnp_dirs():
    """Install the LNP subdirs that I can't create automatically."""
    for d in ('colors', 'embarks', 'extras', 'keybinds', 'tilesets'):
        shutil.copytree(paths.base(d), paths.lnp(d))
    overwrite_dir(paths.lnp('extras'), paths.df())
    with open(paths.lnp('keybinds', 'Vanilla DF.txt'), 'w',
              encoding='cp437') as f:
        f.write('\n')
    for img in {'curses_640x300', 'curses_800x600',
                'curses_square_16x16', 'mouse'}:
        shutil.copy(paths.curr_baseline('data', 'art', img + '.png'),
                    paths.lnp('tilesets'))
    overwrite_dir(paths.lnp('tilesets'), paths.curr_baseline('data', 'art'))
    shutil.copy(paths.curr_baseline('data', 'init', 'colors.txt'),
                paths.lnp('colors', 'ASCII Default.txt'))


def make_defaults():
    """Create and install LNP/Defaults - embark profiles, Phoebus settings."""
    default_dir = paths.lnp('defaults')
    os.makedirs(default_dir)
    shutil.copy(paths.lnp('embarks', 'default_profiles.txt'), default_dir)
    for f in {'init.txt', 'd_init.txt'}:
        shutil.copy(paths.graphics('Phoebus', 'data', 'init', f), default_dir)
    overwrite_dir(default_dir, paths.df('data', 'init'))
    os.rename(paths.df('data', 'init', 'default_profiles.txt'),
              paths.df('data', 'init', 'embark_profiles.txt'))


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
    """Extract all utilities to the build/LNP/Utilities dir."""
    for comp in component.UTILITIES:
        targetdir = paths.lnp(comp.category, comp.name)
        try:
            unzip_to(comp.path, targetdir)
        except IOError:
            if not os.path.isdir(targetdir):
                os.makedirs(targetdir)
            shutil.copy(comp.path, targetdir)
    _soundsense_xml()
    _therapist_ini()
    # Add xml for PerfectWorld, blueprints for Quickfort
    unzip_to(component.ALL['PerfectWorld XML'].path,
             paths.utilities('PerfectWorld'))
    unzip_to(component.ALL['Quickfort Blueprints'].path,
             paths.utilities('Quickfort', 'blueprints'))
    # generate utilities.txt (waiting for a decent utility config format)
    with open(paths.utilities('utilities.txt'), 'w') as f:
        for util in component.UTILITIES:
            exe, jars = [], []
            for _, _, files in os.walk(paths.utilities(util.name)):
                for fname in files:
                    if fname.endswith('.exe'):
                        exe.append(fname)
                    elif fname.endswith('.jar'):
                        jars.append(fname)
            f.write(''.join('[{}:EXCLUDE]\n'.format(j) for j in jars))
            if exe:
                f.write('[{}:{}:{}]\n\n'.format(
                    sorted(exe)[0], util.name, util.tooltip))
            else:
                print('WARNING: no executable for {}'.format(util.name))


def _twbt_settings(pack):
    """Set TwbT-specific options for a graphics pack."""
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


def _make_ascii_graphics():
    """Create the ASCII graphics pack from a DF zip."""
    unzip_to(component.ALL['Dwarf Fortress'].path,
             paths.graphics('ASCII'))
    manifest = {"author": "ToadyOne", "content_version": paths.DF_VERSION,
                "tooltip": "Default graphics for DF, exactly as they come."}
    with open(paths.graphics('ASCII', 'manifest.json'), 'w') as f:
        json.dump(manifest, f, indent=4)


def _install_graphics_pack(pack='Phoebus'):
    """Install the given pack; write installed_raws so PyLNP updates saves."""
    shutil.rmtree(paths.df('raw', 'graphics'))
    overwrite_dir(paths.graphics('Phoebus'), paths.df())
    with open(paths.df('raw', 'installed_raws.txt'), 'w') as f:
        txt = '# List of raws merged by PyLNP:\nbaselines/{}\ngraphics/{}\n'
        f.write(txt.format(os.path.basename(paths.curr_baseline()), pack))


def create_graphics():
    """Extract all graphics packs to the build/LNP/Graphics dir."""
    # Unzip all packs
    for comp in component.GRAPHICS:
        unzip_to(comp.path, paths.lnp(comp.category, comp.name))
    _make_ascii_graphics()
    # Only keep the 24px edition of Gemset
    gemset = glob.glob(paths.graphics('Gemset', '*_24px'))
    if gemset:
        shutil.move(gemset[0], paths.graphics('_temp'))
        shutil.rmtree(paths.graphics('Gemset'))
        shutil.move(paths.graphics('_temp'), paths.graphics('Gemset'))

    for pack in os.listdir(paths.graphics()):
        # Reduce filesize of graphics packs
        rough_simplify(paths.graphics(pack))
        tilesets = os.listdir(paths.lnp('tilesets'))
        for file in os.listdir(paths.graphics(pack, 'data', 'art')):
            if file in tilesets or file.endswith('.bmp'):
                os.remove(paths.graphics(pack, 'data', 'art', file))
        # Check that all is well...
        files = os.listdir(paths.graphics(pack))
        if not ('data' in files and 'raw' in files):
            print(pack + ' graphics pack malformed!')
        elif len(files) > 3:
            print(pack + ' graphics pack not simplified!')
        if os.path.isfile(paths.df('hack', 'plugins', 'twbt.plug.dll')):
            if pack not in {'ASCII', 'Gemset'}:
                _twbt_settings(pack)
    _install_graphics_pack()


def create_df_dir():
    """Create the Dwarf Fortress directory, with DFHack and other content."""
    unzip_to(component.ALL['Dwarf Fortress'].path, paths.df())
    # 0.42.03 bug - can't save macros without this dir; breaks Quickfort
    # http://www.bay12games.com/dwarves/mantisbt/view.php?id=9398
    os.makedirs(paths.df('data', 'init', 'macros'))
    # Several utilities assume gamelog.txt exists and misbehave otherwise
    with open(paths.df('gamelog.txt'), 'w', encoding='cp437') as f:
        f.write('*** STARTING NEW GAME ***\n')

    hack = component.ALL.get('DFHack')
    if not hack:
        print('WARNING:  DFHack not in config, will not be installed.')
        return
    if paths.DF_VERSION not in hack.version:
        print('Incompatible DF, DFHack versions!  Aborting...')
        return
    unzip_to(hack.path, paths.df())
    # Rename the example init file; disable prerelease builds
    os.rename(paths.df('dfhack.init-example'), paths.df('dfhack.init'))
    if '-r' not in hack.version:
        shutil.copy(paths.df('SDL.dll'), paths.df('SDLhack.dll'))
        shutil.copy(paths.df('SDLreal.dll'), paths.df('SDL.dll'))
    # Install Stocksettings
    unzip_to(component.ALL['Stocksettings'].path, paths.df('stocksettings'))
    # install TwbT
    plugins = ['{}/{}.plug.dll'.format(hack.version.replace('v', ''), plug)
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


def create_baselines():
    """Extract the data and raw dirs of vanilla DF to LNP/Baselines."""
    unzip_to(component.ALL['Dwarf Fortress'].path, paths.curr_baseline())
    rough_simplify(paths.curr_baseline())


def _contents():
    """Make LNP/about/contents.txt from a template."""
    def link(comp, ver=True, dash=' - '):
        """Return BBCode format link to the component."""
        vstr = ' ' + comp.version if ver else ''
        return dash + '[url={}]{}[/url]'.format(comp.page, comp.name + vstr)

    kwargs = {c.name: link(c, dash='') for c in component.FILES}
    kwargs['graphics'] = '\n'.join(link(c, False) for c in component.GRAPHICS)
    kwargs['utilities'] = '\n'.join(link(c) for c in component.UTILITIES)
    with open(paths.base('changelog.txt')) as f:
        kwargs['changelogs'] = '\n\n'.join(f.read().split('\n\n')[:5])
    with open(paths.base('contents.txt')) as f:
        template = f.read()
    for item in kwargs:
        if '{' + item + '}' not in template:
            print('WARNING: ' + item + ' not listed in base/docs/contents.txt')
    with open(paths.lnp('about', 'contents.txt'), 'w') as f:
        f.write(template.format(**kwargs))


def create_about():
    """Create the LNP/About folder contents."""
    if not os.path.isdir(paths.lnp('about')):
        os.mkdir(paths.lnp('about'))
    shutil.copy(paths.base('about.txt'), paths.lnp('about'))
    shutil.copy(paths.base('changelog.txt'),
                paths.lnp('about', 'changelog.txt'))
    _contents()


def setup_pylnp():
    """Extract PyLNP and copy PyLNP.json from ./base"""
    unzip_to(component.ALL['PyLNP'].path, paths.build())
    os.rename(paths.build('PyLNP.exe'),
              paths.build('Starter Pack Launcher (PyLNP).exe'))
    os.remove(paths.build('PyLNP.json'))
    with open(paths.base('PyLNP-json.yml')) as f:
        pylnp_conf = yaml.load(f)
    pylnp_conf['updates']['packVersion'] = paths.PACK_VERSION
    with open(paths.lnp('PyLNP.json'), 'w') as f:
        json.dump(pylnp_conf, f, indent=2)


def build_all():
    """Build all components, in the required order."""
    print('\nBuilding pack...')
    if os.path.isdir('build'):
        shutil.rmtree('build')
    create_df_dir()
    create_baselines()
    install_lnp_dirs()
    create_utilities()
    create_graphics()
    setup_pylnp()
    create_about()
    make_defaults()
