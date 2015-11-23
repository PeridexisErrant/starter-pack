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
import json
import os
import shutil
import zipfile

from starterpack import (
    build,
    component,
    configure,
    download,
    paths,
    )

# TODO:  implement the actual logic for this module


def cache_metadata():
    """Prints the name and version of each utility, caching the response."""
    for cat, item in component.ITEMS:
        c = component.Component(cat, item)
        print('{:25}{:15}{}'.format(c.name, c.version, c.filename[:30]))
    with open('_cached.json', 'w') as f:
        json.dump(download.JSON_CACHE, f)


def download_files():
    """Download files which are in config.yml, but not saved in components."""
    for cat, item in component.ITEMS:
        c = component.Component(cat, item)
        if c.download():
            print('Downloaded  {:25}{:30}'.format(c.name, c.filename[:25]))


def build_pack():
    """Copy everything to the 'build' directory, ready to go."""
    shutil.rmtree('build')
    build.create_df_dir()
    build.create_utilities()
    for d in os.listdir(paths.base()):
        if os.path.isdir(paths.base(d)):
            build.overwrite_dir(paths.base(d), paths.lnp(d))
    build.overwrite_dir(paths.lnp('Graphics', 'Phoebus'), paths.df())
    build.pylnp_config()
    configure.configure_all()


cache_metadata()
download_files()
build_pack()


def zip_pack():
    """Zip the pack and return the sha256 of the resulting file."""
    if os.path.isfile(paths.dist()):
        raise ValueError('A zipped version of this pack already exists!')
    with zipfile.ZipFile(paths.dist(), 'w', zipfile.ZIP_DEFLATED) as zf:
        for dirname, _, files in os.walk(paths.pack()):
            zf.write(dirname)
            for filename in files:
                zf.write(os.path.join(dirname, filename))
    with open(paths.dist(), 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()
