"""Zip the built pack and create thread posts."""
# TODO:  save checksums and timestamp in changelog or history file

import hashlib
import json
import os
import re
import shutil
import zipfile

from . import component
from . import paths


def get_contents(kwargs):
    """Read, edit, and format the contents template.  Removes lines for
    missing components and warns if existing components are not listed."""
    with open(paths.base('contents.txt')) as f:
        template = ''.join(l for l in f.readlines() if '{' not in l or
                           re.findall(r'{(.*?)}', l)[0] in kwargs)
    template = template.replace('\n\n\n\n', '\n\n')
    for item in set(re.findall(r'{(.*?)}', template)) - set(kwargs):
        print('WARNING: ' + item + ' not listed in base/docs/contents.txt')
    return template.format(**kwargs)


def create_about():
    """Create the LNP/About folder contents."""
    # Create the folder, copy over forum description and changelog
    if not os.path.isdir(paths.lnp('about')):
        os.mkdir(paths.lnp('about'))
    shutil.copy(paths.base('about.txt'), paths.lnp('about'))
    # TODO:  require changelog to be up to date / complete?
    shutil.copy(paths.base('changelog.txt'),
                paths.lnp('about', 'changelog.txt'))

    def link(comp, ver=True, dash=' - '):
        """Return BBCode format link to the component."""
        vstr = ' ' + comp.version if ver else ''
        return dash + '[url={}]{}[/url]'.format(comp.page, comp.name + vstr)

    # Create the table of contents
    kwargs = {c.name: link(c, dash='') for c in component.FILES}
    kwargs['graphics'] = '\n'.join(link(c, False) for c in component.GRAPHICS)
    kwargs['utilities'] = '\n'.join(link(c) for c in component.UTILITIES)
    with open(paths.base('changelog.txt')) as f:
        kwargs['changelogs'] = '\n\n'.join(f.read().split('\n\n')[:5])
    with open(paths.lnp('about', 'contents.txt'), 'w') as f:
        f.write(get_contents(kwargs))


def zip_pack():
    """Compress the build dir to a zipped pack."""
    os.makedirs(paths.dist(), exist_ok=True)
    with zipfile.ZipFile(paths.zipped(), 'w', zipfile.ZIP_DEFLATED) as zf:
        for dirname, _, files in os.walk(paths.build()):
            zf.write(dirname, os.path.relpath(dirname, paths.build()))
            for filename in files:
                fname = os.path.join(dirname, filename)
                zf.write(fname, os.path.relpath(fname, paths.build()))


def release_docs():
    """Document the file checksum and create a forum post."""
    if paths.ARGS.stable:
        shutil.copy(paths.lnp('about', 'contents.txt'), paths.dist())
    with open(paths.lnp('PyLNP.json')) as config:
        dffd_id = json.load(config)['updates']['dffdID']
    with open(paths.lnp('about', 'changelog.txt')) as f:
        changes = f.read().split('\n\n')[0]
    sha256 = hashlib.sha256()
    with open(paths.zipped(), 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    post_kwargs = {
        'PACK_VERSION': paths.pack_ver(warn=False),
        'LINK': 'http://dffd.bay12games.com/file.php?id=' + dffd_id,
        'CHANGELOG': changes,
        'CHECKSUM': sha256.hexdigest(),
        'BITS': paths.BITS,
        }
    key = 'forum_post' if paths.ARGS.stable else 'unstable_forum_post'
    with open(paths.dist('forum_post.txt'), 'w') as f:
        f.write(paths.CONFIG.get(key, '')
                .replace('_\n', '\n').format(**post_kwargs))
        if not paths.ARGS.stable:
            with open(paths.lnp('about', 'contents.txt')) as contents:
                f.write('\n[spoiler=Full contents]\n')
                f.write(contents.read())
                f.write('\n[/spoiler]')


def main():
    """Make the dist folder."""
    create_about()
    print('\nCompressing pack...')
    zip_pack()
    release_docs()
    print('Pack zipped in ./dist/ and ready to inspect.')
