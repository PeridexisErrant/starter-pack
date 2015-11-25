"""Configure various components of PeridexisErrant's Starter Pack.

Logic in this module is subject to change without notice based on
upstream changes or to alter the default configuration of the pack.
"""

import os
import shutil

import requests

from . import build
from . import paths


def install_lnp_dirs():
    """Install the LNP subdirs that I can't create automatically."""
    for d in ('Colours', 'Embarks', 'Extras', 'Tilesets'):
        shutil.copytree(paths.base(d), paths.lnp(d))
    build.overwrite_dir(paths.lnp('Extras'), paths.df())
    build.overwrite_dir(paths.lnp('Tilesets'), paths.df('data', 'art'))


def make_baselines():
    """Extract the data and raw dirs of vanilla DF to LNP/Baselines."""
    df_zip = paths.component_by_name('Dwarf Fortress')
    base_dir = df_zip.replace('_win', '').replace('.zip', '')
    build.unzip_to(df_zip, paths.lnp('Baselines', base_dir))
    # TODO: remove other files


def make_defaults():
    """Create and install LNP/Defaults files from the vanilla files."""
    default_dir = paths.lnp('Defaults')
    shutil.copy(paths.lnp('Embarks', 'default_profiles.txt'), default_dir)
    # TODO: also create and edit init.txt, d_init.txt
    raise NotImplementedError
    build.overwrite_dir(default_dir, paths.df('data', 'init'))


def make_keybindings():
    """Create and install LNP/keybindings files from the vanilla files."""
    os.makedirs(paths.lnp('Keybindings'))
    # Read/write vanilla keybindings
    with open(paths.df('data', 'init', 'interface.txt'),
              encoding='cp437') as f:
        dflines = f.readlines()
    with open(paths.lnp('Keybindings', 'Vanilla DF.txt'), 'w') as f:
        f.write(dflines)
    # Then write modified versions for 'Laptop' and 'Laptop with mouse' keys
    # TODO: implement this function


def check_installed_settings():
    """Checks that default settings are installed"""
    with open(paths.df('data', 'init', 'd_init.txt')) as f:
        if not '[ENGRAVINGS_START_OBSCURED:YES]' in f.read():
            print('{:30}{}'.format('Default settings', 'need installation'))


def soundsense_xml():
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


def graphics_simplified():
    """Check that graphics packs are all configured correctly."""
    for p in os.listdir(paths.graphics()):
        files = os.listdir(paths.graphics(p))
        if not ('data' in files and 'raw' in files):
            print('{:30}{}'.format(p + ' graphics pack', 'malformed'))
        elif len(files) > 3:
            # data, raw, manifest.json
            print('{:30}{}'.format(p + ' graphics pack', 'not simplified'))


def dwarf_therapist():
    """Check that DT memory layout for the current version is present."""
    fname = 'v{}_graphics.ini'.format(paths.DF_VERSION)
    memfile = paths.utilities(
        'Dwarf Therapist', 'share', 'memory_layouts', 'windows', fname)
    if os.path.isfile(memfile):
        return
    if not os.path.isfile(paths.component(fname)):
        # TODO:  update this URL scheme for next DF version
        url = ('https://raw.githubusercontent.com/splintermind/Dwarf-Therapist'
               '/DF2014/share/memory_layouts/windows/' + fname)
        text = requests.get(url).text
        with open(memfile, 'w') as f:
            f.write(text)
        print('{:30}{}'.format('Therapist memory layout', 'was downloaded'))
    shutil.copy(paths.component(fname), memfile)


def twbt_config_and_files():
    """Check and update init files for TwbT settings."""
    # ASCII doesn't use TwbT - it's the vanilla interface
    # Gemset is built for TwbT and doesn't need configuring
    # CLA uses multilevel, but no overrides.
    # Other packs need printmode and FONT changed
    # TODO: check whether this is required after Fricy updates...
    for pack in [p for p in os.listdir(paths.graphics())
                 if p not in {'ASCII', 'Gemset'}]:
        ors = paths.graphics(pack, 'data', 'init', 'overrides.txt')
        if not os.path.isfile(ors) and pack != 'CLA':
            print('{:30}{}'.format(pack + ' TwbT graphics', 'needs overrides'))
        init_file = paths.graphics(pack, 'data', 'init', 'init.txt')
        with open(init_file) as f:
            init = f.readlines()
            orig = init[:]
        for n, _ in enumerate(init):
            if init[n].startswith('[FONT:') and pack != 'CLA':
                init[n] = '[FONT:curses_640x300.png]\n'
            elif init[n].startswith('[FULLFONT:') and pack != 'CLA':
                init[n] = '[FULLFONT:curses_640x300.png]\n'
            elif init[n].startswith('[PRINT_MODE:'):
                init[n] = '[PRINT_MODE:TWBT]\n'
        if init != orig:
            with open(init_file, 'w') as f:
                f.writelines(init)


def configure_all():
    """Call all the configuration functions above."""
    install_lnp_dirs()
    make_baselines()
    make_defaults()
    make_keybindings()
    soundsense_xml()
    graphics_simplified()
    check_installed_settings()
    dwarf_therapist()
    twbt_config_and_files()
