"""Configure various components of PeridexisErrant's Starter Pack.

Logic in this module is subject to change without notice based on
upstream changes or to alter the default configuration of the pack.
"""

import glob
import os
import shutil

import requests

from . import paths
from . import versions


def result(part, status, last=['']):
    """Shortcut to print values and remember overall status"""
    if part != last[0]:
        print('{:30}{}'.format(part, status))
        last[0] = part


def check_installed_settings():
    """Checks that default settings are installed"""
    with open(paths.df('data', 'init', 'd_init.txt')) as f:
        if not '[ENGRAVINGS_START_OBSCURED:YES]' in f.read():
            result('Default settings', 'need installation')


def check_extras():
    """Check that extras are installed"""
    # only checks top-level files and folders
    extras = paths.lnp('extras', '*')
    files = [os.path.relpath(f, os.path.dirname(extras))
             for f in glob.glob(extras)]
    if not all([os.path.exists(paths.df(f)) for f in files]):
        result('Extras files', 'need installation')


def keybinds():
    """Check that keybindings haven't changed between versions"""
    installed = paths.df('data', 'init', 'interface.txt')
    stored = paths.lnp('keybinds', 'Vanilla DF.txt')
    with open(stored, encoding='cp437') as f1:
        with open(installed, encoding='cp437') as f2:
            if not f1.read() == f2.read():
                result('Keybinds status', 'needs updating')
    result('Keybinds status', 'is OK')


def embark_profiles():
    """Check if embark profiles are installed, and if not copy them from
    defaults folder."""
    default = paths.lnp('defaults', 'embark_profiles.txt')
    installed = paths.df('data', 'init', 'embark_profiles.txt')
    if os.path.isfile(installed):
        result('Embark profile install', 'is OK')
    else:
        shutil.copyfile(default, installed)
        result('Embark profile install', 'was fixed')


def soundsense_xml():
    """Check and update version strings in xml path config"""
    xmlfile = paths.utilities('soundsense', 'configuration.xml')
    with open(xmlfile) as f:
        config = f.readlines()
        orig = config[:]
    for n, _ in enumerate(config):
        if r'\gamelog.txt"/>' in config[n]:
            config[n] = ('\t<gamelog encoding="Cp850" path="..\\..\\..\\' +
                         versions.df(dirname=True) + '\\gamelog.txt"/>\n')
        if r'\ss_fix.log"/>' in config[n]:
            config[n] = ('\t\t<item path="..\\..\\..\\' +
                         versions.df(dirname=True) +
                         '\\ss_fix.log"/>\n')
    if not config == orig:
        with open(xmlfile, 'w') as f:
            f.writelines(config)
        result('Soundsense configuration', 'was fixed')
    result('Soundsense configuration', 'is OK')


def graphics_installed_and_all_simplified():
    """Check that I haven't forgotten to simplify or installa graphics pack."""
    # later, can I pull from Fricy's repo to fix this?
    packs = ['ASCII Default', 'CLA', 'Ironhand', 'Mayday',
             'Obsidian', 'Phoebus', 'Spacefox']
    available = os.listdir(paths.lnp('graphics'))
    if not all([(p in available) for p in packs]):
        result('graphics packs set', 'not correct')
    for p in packs:
        if os.path.isfile(paths.lnp('graphics', p, 'Dwarf Fortress.exe')):
            result(p + ' graphics pack', 'not simplified')
    if os.path.isfile(paths.df('data', 'art', 'Phoebus_16x16.png')):
        result('Phoebus graphics install', 'is OK')
    result('Phoebus graphics install', 'not installed')


def dwarf_therapist():
    """Check that DT memory layout for the current version is present."""
    fname = 'v{}_graphics.ini'.format(versions.df())
    for folder in glob.glob(paths.utilities('Dwarf*Therapist*')):
        memfile = os.path.join(folder, 'share', 'memory_layouts', 'windows',
                               fname)
        break
    if os.path.isfile(memfile):
        result('Therapist memory layout', 'is OK')
    else:
        url = ('https://raw.githubusercontent.com/splintermind/Dwarf-Therapist'
               '/DF2014/share/memory_layouts/windows/' + fname)
        try:
            with open(memfile, 'w') as f:
                f.write(requests.get(url).text)
            result('Therapist memory layout', 'was downloaded')
        except Exception:
            result('Therapist memory layout', 'not available')


def twbt_config_and_files():
    """Check if TwbT is installed."""
    if not os.path.isfile(paths.df('hack', 'plugins', 'twbt.plug.dll')):
        result('TwbT plugin', 'not installed')
        return
    g = [p for p in os.listdir(paths.lnp('graphics'))
         if os.path.isdir(paths.lnp('graphics', p)) and not 'ascii' in p.lower()]
    for pack in g:
        ors = paths.lnp('graphics', pack, 'data', 'init', 'overrides.txt')
        if not os.path.isfile(ors):
            result(pack + ' TwbT graphics', 'needs overrides')
        twbtify_graphics_init(pack)


def twbtify_graphics_init(pack):
    """Get TwbT init settings working for a graphics pack"""
    if 'gemset' in pack.lower():
        return #designed for TwbT, do not retrofit
    init_file = paths.lnp('graphics', pack, 'data', 'init', 'init.txt')
    with open(init_file) as f:
        init = f.readlines()
        orig = init[:]
    for n, _ in enumerate(init):
        if init[n].startswith('[FONT:'):
            init[n] = '[FONT:curses_640x300.png]\n'
        elif init[n].startswith('[FULLFONT:'):
            init[n] = '[FULLFONT:curses_640x300.png]\n'
        elif init[n].startswith('[PRINT_MODE:'):
            init[n] = '[PRINT_MODE:TWBT]\n'
    if init != orig:
        with open(init_file, 'w') as f:
            f.writelines(init)
        result(pack + ' TwbT graphics', 'was fixed')


def configure_all():
    print('Checking built pack is configured...')
    keybinds()
    embark_profiles()
    soundsense_xml()
    graphics_installed_and_all_simplified()
    check_installed_settings()
    check_extras()
    dwarf_therapist()
    twbt_config_and_files()
