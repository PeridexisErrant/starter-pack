"""Zip the built pack and create thread posts."""

import os
import shutil
import zipfile

from . import paths
# TODO: warn if recent updates are not reflected in the changelog

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
    with open(paths.lnp('about', 'changelog.txt')) as f:
        s = ('The Starter Pack has updated to {}!  As usual, [url=http://dffd'
             '.bay12games.com/file.php?id=7622]you can get it here.[/url]\n\n'
             '\n\n{}').format(paths.PACK_VERSION, f.read().split('\n\n')[0])
    with open(paths.dist('forum_post.txt'), 'w') as f:
        f.write(s)
    # TODO:  find a reasonably elegant way to document checksum, timestamp


def make():
    """Make the dist folder."""
    print('\nCompressing pack...')
    zip_pack()
    release_docs()
    print('Pack zipped in ./dist/ and ready to inspect.')
