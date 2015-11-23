"""Manage documentation for the pack.

Mostly involves cut/edit/paste logic.
Currently unfinished and unusable.
Needs reworking to be useful.
"""

from .configure import result
from . import paths
from . import versions

# TODO: modularise this, break down into chunks, automate more stuff


def update_documentation():
    """Check contents list, changelog, and documentation."""
    doc_file = paths.lnp('About', 'pack contents and changelog.txt')
    with open(doc_file) as f:
        lines = f.readlines()
        orig = lines[:]
    in_cl, table_r = False, 0
    for n, _ in enumerate(lines):
        if lines[n].startswith('[tr][td]'):
            table_r += 1
            if versions.starter_pack() in lines[n]:
                if table_r == 2:
                    lines[n] = '[tr][td]{}[/td][td]unavailable[/td][/tr]\n'\
                               .format(versions.starter_pack())
                    continue
                else:
                    lines[n] = ''
            if table_r == 2:
                lines[n] = '[tr][td]{}[/td][td]unavailable[/td][/tr]\n{}'\
                           .format(versions.starter_pack(), lines[n])
        if in_cl:
            if lines[n] == '\n':
                in_cl = False
            if lines[n] == ' - \n':
                lines[n] = ''
        if lines[n].startswith(versions.starter_pack()):
            in_cl = True
    if not lines == orig:
        with open(doc_file, 'w') as f:
            f.writelines(lines)
        result('Pack documentation', 'was fixed')
    result('Pack documentation', 'is OK')


def check_documentation():
    """Check contents list, changelog, and documentation."""
    doc_file = paths.lnp('About', 'pack contents and changelog.txt')
    with open(doc_file) as f:
        lines = f.readlines()
        orig = lines[:]
    in_cl, table_r = False, 0
    for n, _ in enumerate(lines):
        if lines[n].startswith('[tr][td]'):
            table_r += 1
            if versions.starter_pack() in lines[n]:
                if table_r == 2:
                    lines[n] = '[tr][td]{}[/td][td]unavailable[/td][/tr]\n'\
                               .format(versions.starter_pack())
                    continue
                else:
                    lines[n] = ''
            if table_r == 2:
                lines[n] = '[tr][td]{}[/td][td]unavailable[/td][/tr]\n{}'\
                           .format(versions.starter_pack(), lines[n])
        if in_cl:
            if lines[n] == '\n':
                in_cl = False
            if lines[n] == ' - \n':
                lines[n] = ''
        if lines[n].startswith(versions.starter_pack()):
            in_cl = True
    if not lines == orig:
        with open(doc_file, 'w') as f:
            f.writelines(lines)


def release_documentation(SHA256):
    """Produces documentation ready for copy-pasting online"""
    doc_file = paths.lnp('About', 'pack contents and changelog.txt')
    # Update documentation with checksum
    with open(doc_file) as f:
        text = f.read()
    text = text.replace('[td]unavailable[/td]', '[td]' + SHA256 + '[/td]')
    with open(doc_file, 'w') as f:
        f.write(text)
    # Main post for Bay12 forums is pre-written and just updated
    with open(path.dist('contents_and_changelog.txt'), 'w') as f:
        f.write(text)
    # Get changelog - everything but first line
    changelog = []
    with open('contents_and_changelog.txt') as f:
        for k in f.readlines():
            if k.strip() == versions.starter_pack(dirname=True):
                changelog.append('Changelog:\n')
                continue
            if changelog:
                changelog.append(k)
                if k == '\n':
                    break
    changelog.append('SHA256:  ' + SHA256)
    # Write summaries
    dffd_url = 'http://dffd.bay12games.com/file.php?id=7622'
    with open('forum_post.txt', 'w') as f:
        f.write('The Starter Pack has updated to ' + versions.starter_pack() +
                '!  As usual, [url=' + dffd_url + ']'
                'you can get it here.[/url]\n\n')
        f.writelines(changelog)
    with open('reddit_post.txt', 'w') as f:
        f.write('The Starter Pack has updated to ' + versions.starter_pack() +
                '!  As usual, [you can get it here.]'
                '(' + dffd_url + ')\n\n')
        f.writelines(['    ' + k for k in changelog])
