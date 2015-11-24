"""Configure various components of PeridexisErrant's Starter Pack.

Logic in this module is subject to change without notice based on
upstream changes or to alter the default configuration of the pack.
"""

import glob
import os
import shutil

import requests

from . import paths


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
    result('Soundsense configuration', 'was fixed')


def graphics_simplified():
    """Check that graphics packs are all configured correctly."""
    for p in os.listdir(paths.lnp('graphics')):
        files = os.listdir(paths.lnp('graphics', p))
        if not ('data' in files and 'raw' in files):
            result(p + ' graphics pack', 'malformed')
        elif len(files) > 3:
            # data, raw, manifest.json
            result(p + ' graphics pack', 'not simplified')


def dwarf_therapist():
    """Check that DT memory layout for the current version is present."""
    fname = 'v{}_graphics.ini'.format(versions.df())
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
        result('Therapist memory layout', 'was downloaded')
    shutil.copy(paths.component(fname), memfile)


def twbt_config_and_files():
    """Check if TwbT is installed."""
    if not os.path.isfile(paths.df('hack', 'plugins', 'twbt.plug.dll')):
        result('TwbT plugin', 'not installed')
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
    graphics_simplified()
    check_installed_settings()
    dwarf_therapist()
    twbt_config_and_files()
