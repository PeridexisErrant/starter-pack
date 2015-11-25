"""Manage documentation for the pack.

Mostly involves cut/edit/paste logic.
Currently unfinished and unusable.
Needs reworking to be useful.
"""

from . import paths

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
            if paths.PACK_VERSION in lines[n]:
                if table_r == 2:
                    lines[n] = '[tr][td]{}[/td][td]unavailable[/td][/tr]\n'\
                               .format(paths.PACK_VERSION)
                    continue
                else:
                    lines[n] = ''
            if table_r == 2:
                lines[n] = '[tr][td]{}[/td][td]unavailable[/td][/tr]\n{}'\
                           .format(paths.PACK_VERSION, lines[n])
        if in_cl:
            if lines[n] == '\n':
                in_cl = False
            if lines[n] == ' - \n':
                lines[n] = ''
        if lines[n].startswith(paths.PACK_VERSION):
            in_cl = True
    if not lines == orig:
        with open(doc_file, 'w') as f:
            f.writelines(lines)


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
            if paths.PACK_VERSION in lines[n]:
                if table_r == 2:
                    lines[n] = '[tr][td]{}[/td][td]unavailable[/td][/tr]\n'\
                               .format(paths.PACK_VERSION)
                    continue
                else:
                    lines[n] = ''
            if table_r == 2:
                lines[n] = '[tr][td]{}[/td][td]unavailable[/td][/tr]\n{}'\
                           .format(paths.PACK_VERSION, lines[n])
        if in_cl:
            if lines[n] == '\n':
                in_cl = False
            if lines[n] == ' - \n':
                lines[n] = ''
        if lines[n].startswith(paths.PACK_VERSION):
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
    with open(paths.dist('contents_and_changelog.txt'), 'w') as f:
        f.write(text)
    # Get changelog - everything but first line
    changelog = []
    with open('contents_and_changelog.txt') as f:
        for k in f.readlines():
            if k.strip() == paths.PACK_VERSION:
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
        f.write('The Starter Pack has updated to ' + paths.PACK_VERSION +
                '!  As usual, [url=' + dffd_url + ']'
                'you can get it here.[/url]\n\n')
        f.writelines(changelog)
    with open('reddit_post.txt', 'w') as f:
        f.write('The Starter Pack has updated to ' + paths.PACK_VERSION +
                '!  As usual, [you can get it here.]'
                '(' + dffd_url + ')\n\n')
        f.writelines(['    ' + k for k in changelog])
