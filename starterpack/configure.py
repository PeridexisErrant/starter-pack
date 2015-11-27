"""Configure various components of PeridexisErrant's Starter Pack.

Logic in this module is subject to change without notice based on
upstream changes or to alter the default configuration of the pack.
"""

import collections
import datetime
import os
import shutil

from . import build
from . import component
from . import paths


def install_lnp_dirs():
    """Install the LNP subdirs that I can't create automatically."""
    for d in ('colors', 'embarks', 'extras', 'tilesets'):
        shutil.copytree(paths.base(d), paths.lnp(d))
    build.overwrite_dir(paths.lnp('extras'), paths.df())
    for img in {'curses_640x300', 'curses_800x600',
                'curses_square_16x16', 'mouse'}:
        shutil.copy(paths.curr_baseline('data', 'art', img + '.png'),
                    paths.lnp('tilesets'))
    build.overwrite_dir(paths.lnp('tilesets'), paths.df('data', 'art'))


def make_defaults():
    """Create and install LNP/Defaults - embark profiles, Phoebus settings."""
    default_dir = paths.lnp('Defaults')
    shutil.copy(paths.lnp('embarks', 'default_profiles.txt'), default_dir)
    for f in {'init.txt', 'd_init.txt'}:
        shutil.copy(paths.graphics('Phoebus', 'data', 'init', f), default_dir)
    build.overwrite_dir(default_dir, paths.df('data', 'init'))


def make_keybindings():
    """Create and install LNP/keybindings files from the vanilla files."""
    os.makedirs(paths.lnp('keybindings'))
    van_file = paths.df('data', 'init', 'interface.txt')
    shutil.copy(van_file, paths.lnp('keybindings', 'Vanilla DF.txt'))

    def keybinds_serialiser(lines):
        """Turn lines into an ordered dict, to preserve structure of file."""
        od, lastkey = collections.OrderedDict(), None
        for line in (l.strip() for l in lines):
            if line and line.startswith('[BIND:'):
                od[line], lastkey = [], line
            elif line:
                if lastkey is not None:
                    od[lastkey].append(line)
        return od

    with open(van_file, encoding='cp437') as f:
        vanbinds = keybinds_serialiser(f.readlines())
    for fname in os.listdir(paths.base('keybindings')):
        with open(paths.base('keybindings', fname)) as f:
            cfg = keybinds_serialiser(f.readlines())
        lines = []
        for bind, vals in vanbinds.items():
            lines.append(bind)
            if bind in cfg:
                lines.extend(cfg[bind])
            else:
                lines.extend(vals)
        with open(paths.lnp('keybindings', fname), 'w', encoding='cp437') as f:
            f.write('\n' + '\n'.join(lines))


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


def twbt_config_and_files():
    """Check and update init files for TwbT settings.

    ASCII doesn't use TwbT.  CLA uses multilevel, but no overrides.
    Gemset is built for TwbT.  Other packs need printmode and FONT changed.
    """
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


def update_docs():
    """Copy about and changelog; add date to latest changelog."""
    if not os.path.isdir(paths.lnp('about')):
        os.mkdir(paths.lnp('about'))
    shutil.copy(paths.base('about.txt'), paths.lnp('about'))
    with open(paths.base('changelog.txt')) as f:
        changelog = f.readlines()
        changelog.insert(0, 'Version {} ({})\n'.format(
            paths.PACK_VERSION, datetime.date.today().isoformat()))
        with open(paths.lnp('about', 'changelog.txt'), 'w') as f:
            f.writelines(changelog)


def generate_contents():
    """Generate the contents post from a template (base/contents.txt)."""
    #pylint:disable=missing-docstring
    def link(comp, ver=True, dash=' - '):
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
            raise ValueError(item + ' not listed in base/docs/contents.txt')
    with open(paths.lnp('about', 'contents.txt'), 'w') as f:
        #pylint:disable=star-args
        f.write(template.format(**kwargs))


def configure_all():
    """Call all the configuration functions above."""
    install_lnp_dirs()
    make_defaults()
    make_keybindings()
    soundsense_xml()
    graphics_simplified()
    twbt_config_and_files()
    update_docs()
    generate_contents()
    build.overwrite_dir(paths.graphics('Phoebus'), paths.df())
