"""
Prepare a release of PeridexisErrant's Starter Pack for Dwarf Fortress.

Downloads and checks versions, assembles components, checks configuration,
and perpares everything for upload.

This code is highly specific to my pack - it's released under the GPL3,
but don't expect it to be production-quality or particularly reusable.

It's not finished, but I hope to use it for the 2015/16 release cycle.


Notes:
- configuration is stored in .yaml files (tracked by git)
- files are downloaded to ./components/
    - rebuildable at cost of some download time
- the pack is created in ./build/
    - rebuildable from components; routinely deleted
- the zipped pack to upload, forum posts, etc are created in ./dist/
    - trivial to rebuild from ./build/

"""

import hashlib
import os
import shutil
import zipfile

from starterpack import (
    build,
    component,
    configure,
    paths,
    )


def download_files():
    """Download files which are in config.yml, but not saved in components."""
    for c in component.COMPONENTS:
        if c.download():
            print('Downloaded  {:25}{:30}'.format(c.name, c.filename[:25]))


def build_pack():
    """Copy everything to the 'build' directory, ready to go."""
    shutil.rmtree('build')
    build.build_all()
    configure.configure_all()
    # TODO:  write, call remaining functionality


def zip_pack(*, overwrite=False):
    """Zip the pack and return the sha256 of the resulting file."""
    if not os.path.isdir(paths.dist()):
        os.makedirs(paths.dist())
    elif not overwrite and os.path.isfile(paths.zipped()):
        print('A zipped version of this pack already exists!  Aborting...')
        return
    with zipfile.ZipFile(paths.zipped(), 'w', zipfile.ZIP_DEFLATED) as zf:
        for dirname, _, files in os.walk(paths.build()):
            zf.write(dirname, os.path.relpath(dirname, paths.build()))
            for filename in files:
                fname = os.path.join(dirname, filename)
                zf.write(fname, os.path.relpath(fname, paths.build()))
    with open(paths.zipped(), 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()


if __name__ == '__main__':
    download_files()
    build_pack()
    zip_pack(overwrite=True)
    print('Pack zipped in ./dist/ and ready to inspect.')
