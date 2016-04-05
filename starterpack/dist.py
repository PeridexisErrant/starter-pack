"""Zip the built pack and create thread posts."""
# TODO:  save checksums and timestamp in changelog or history file

import hashlib
import os
import shutil
import zipfile

import yaml

from . import component
from . import paths


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
    with open(paths.base('contents.txt')) as f:
        template = f.read()
    for item in kwargs:
        if '{' + item + '}' not in template:
            print('WARNING: ' + item + ' not listed in base/docs/contents.txt')
    with open(paths.lnp('about', 'contents.txt'), 'w') as f:
        f.write(template.format(**kwargs))


def zip_pack():
    """Compress the build dir to a zipped pack."""
    if not os.path.isdir(paths.dist()):
        os.makedirs(paths.dist())
    with zipfile.ZipFile(paths.zipped(), 'w', zipfile.ZIP_DEFLATED) as zf:
        for dirname, _, files in os.walk(paths.build()):
            zf.write(dirname, os.path.relpath(dirname, paths.build()))
            for filename in files:
                fname = os.path.join(dirname, filename)
                zf.write(fname, os.path.relpath(fname, paths.build()))


def release_docs():
    """Document the file checksum and create a forum post."""
    shutil.copy(paths.lnp('about', 'contents.txt'), paths.dist())
    with open(paths.base('PyLNP-json.yml')) as config:
        dffd_id = yaml.load(config)['updates']['dffdID']
    with open(paths.lnp('about', 'changelog.txt')) as f:
        changes = f.read().split('\n\n')[0]
    sha256 = hashlib.sha256()
    with open(paths.zipped(), 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    checksum = sha256.hexdigest()
    s = paths.CONFIG.get('forum_post', '').format(paths.pack_ver(), dffd_id) +\
        '\n\n\n\n{}\n\nSHA256:  {}'.format(changes, checksum)
    with open(paths.dist('forum_post.txt'), 'w') as f:
        f.write(s)


def main():
    """Make the dist folder."""
    create_about()
    print('\nCompressing pack...')
    zip_pack()
    release_docs()
    print('Pack zipped in ./dist/ and ready to inspect.')
