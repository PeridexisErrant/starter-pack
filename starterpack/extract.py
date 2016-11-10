"""Unpack downloaded files to the appropriate place.

This module is about as generic as it can usefully be, pushing the special
cases back into build.py
"""

import concurrent.futures
from distutils.dir_util import copy_tree
import os
import shutil
import subprocess
import tarfile
import tempfile
import time
import zipfile

from . import component
from . import paths


def _copyfile(src, dest):
    """Copy the source file path or object to the dest path, creating dirs."""
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if isinstance(src, str):
        shutil.copy2(src, dest)
    else:
        with open(dest, 'wb') as out:
            shutil.copyfileobj(src, out)


def unzip_to(filename, target_dir=None, path_pairs=None):
    """Extract the contents of the given archive to the target directory.

    In 'target_dir' mode, extracts the least-nested contents to the target
    directory.  This makes a zip-of-one-dir equivalent to zip-of-several-files.

    In 'path_pairs' mode, the argument should be a sequence of paths.
    The file at the first path within the zip is written at the second path.
    """
    assert bool(target_dir) != bool(path_pairs), 'Choose one unzip mode!'
    out = target_dir or os.path.commonpath([p[1] for p in path_pairs])
    print('{:28}  ->  {}'.format(os.path.basename(filename)[:28],
                                 os.path.relpath(out, paths.build())))

    if path_pairs is not None or filename.endswith('.exe') \
            or not zipfile.is_zipfile(filename):
        # ensures consistent handling for path_pairs
        return nonzip_extract(filename, target_dir, path_pairs)
    # More complex, but faster for zips to do it this way
    with zipfile.ZipFile(filename) as zf:
        files = dict(a for a in zip(zf.namelist(), zf.infolist())
                     if not a[0].endswith('/'))
        prefix = os.path.commonpath(list(files)) if len(files) > 1 else ''
        for name in files:
            out = os.path.join(target_dir, os.path.relpath(name, prefix))
            _copyfile(zf.open(files[name]), out)


def nonzip_extract(filename, target_dir=None, path_pairs=None):
    """An alternative to `unzip_to`, for non-zip archives.

    Extract to tempdir, copy files to destination/path_pairs, remove tempdir.

    Involves a lot of shelling out, as Python's `tarfile` cannot open
    the .tar.bz2 archived DF releases (complicated header issue).
    OSX disk images (.dmg) are also unsupported by Python.
    """
    if filename.endswith('.exe') and paths.HOST_OS == 'win':
        return _copyfile(
            filename, os.path.join(target_dir, os.path.basename(filename)))

    with tempfile.TemporaryDirectory() as tmpdir:
        if not unpack_anything(filename, tmpdir):
            return
        # Copy from tempdir to destination
        files = [os.path.join(root, f)
                 for root, _, files in os.walk(tmpdir) for f in files]
        prefix = os.path.commonpath(files) if len(files) > 1 else ''
        if target_dir:
            copy_tree(os.path.join(tmpdir, prefix), target_dir)
        else:
            for inpath, outpath in path_pairs:
                inpath = os.path.join(prefix, inpath)
                if outpath.endswith('/'):
                    outpath += os.path.basename(inpath)
                if os.path.isfile(os.path.join(tmpdir, inpath)):
                    _copyfile(os.path.join(tmpdir, inpath), outpath)
                else:
                    print('WARNING:  {} not in {}'.format(inpath, filename))


def unpack_anything(filename, tmpdir):
    """Extract practically any archive format from src file to dest dir."""
    if filename.endswith('.dmg') and paths.HOST_OS == 'osx':
        # TODO:  support .dmg extraction via shell on OSX
        raise NotImplementedError(
            'TODO: mount .dmg, copy contents to tmpdir, unmount')
    elif zipfile.is_zipfile(filename):
        # Uses fast version above; handled here for completeness
        zipfile.ZipFile(filename).extractall(tmpdir)
        return True
    elif any(filename.endswith('.tar.' + ext) for ext in ('bz2', 'xz', 'gz'))\
            or tarfile.is_tarfile(filename):
        try:
            tarfile.TarFile(filename).extractall(tmpdir)
            return True
        except tarfile.ReadError:
            try:
                subprocess.run(['tar', '-xf', filename, '-C', tmpdir],
                               check=True)
            except subprocess.CalledProcessError:
                print('ERROR: could not extract ' + filename +
                      ' by tarfile lib or `tar` in shell')
                return False
    elif filename.endswith('.rar'):
        try:
            import rarfile
        except ImportError:
            print('ERROR: .rar not supported; `pip install rarfile` and retry')
            return False
        rarfile.RarFile(filename).extractall(tmpdir)
        return True
    elif filename.endswith('.7z') or filename.endswith('.7zip'):
        if paths.HOST_OS == 'win':
            exe = r'C:\Program Files\7-Zip\7z.exe'
            if not os.path.isfile(exe):
                exe = exe.replace('Program Files', 'Program Files (x86)')
                if not os.path.isfile(exe):
                    print('7z.exe unavailable; install 7zip and try again...')
                    return False
            try:
                args = '"{}" x "{}" -o"{}"'.format(exe, filename, tmpdir)
                subprocess.run(args, check=True, stdout=subprocess.DEVNULL)
                return True
            except subprocess.CalledProcessError as e:
                print('ERROR: 7z.exe failed to extract ' + filename)
                print(e.stderr)
                return False
    print('Error: skipping unsupported archive format ' + filename)
    return False


def extract_comp(pool, comp):
    """Return args with which comp can be sent to the executor."""
    if ':' not in comp.extract_to:
        # first part of extract_to is paths method, remainder is args
        dest, *details = comp.extract_to.split('/')
        return pool.submit(unzip_to, comp.path, getattr(paths, dest)(*details))
    # else using the path_pairs option; extract pairs from string
    pairs = []
    for pair in comp.extract_to.strip().split('\n'):
        src, to = pair.split(':')
        dest, *details = to.split('/')
        # Note: can add format variables here as needed
        if '{DFHACK_VER}' in src:
            src = src.format(DFHACK_VER=component.ALL['DFHack'].version)
        pairs.append([src, getattr(paths, dest)(*details)])
    return pool.submit(unzip_to, comp.path, None, pairs)


def extract_everything():
    """Extract everything in components.yml, respecting order requirements."""
    def q_key(comp):
        """Decide extract priority by pointer-chase depth, filesize in ties."""
        after = {c.install_after: c.name for c in component.ALL.values()}
        name, score = comp.name, 0
        while name in after:
            name, score = after.get(name), score + 1
        return score, os.path.getsize(comp.path)

    queue = list(component.ALL.values()) + [
        component.ALL['Dwarf Fortress']._replace(name=path, extract_to=path)
        for path in ('curr_baseline', 'graphics/ASCII')]
    queue.sort(key=q_key, reverse=True)
    with concurrent.futures.ProcessPoolExecutor(8) as pool:
        futures = dict()
        while queue:
            while queue and sum(f.running() for f in futures.values()) < 8:
                for idx, comp in enumerate(queue):
                    aft = comp.install_after
                    if not aft or (aft in futures and futures[aft].done()):
                        futures[comp.name] = extract_comp(pool, queue.pop(idx))
            time.sleep(0.01)


def add_lnp_dirs():
    """Install the LNP subdirs that I can't create automatically."""
    # Should use https://github.com/Lazy-Newb-Pack/LNP-shared-core someday...
    for d in ('colors', 'embarks', 'extras', 'keybinds', 'tilesets'):
        copy_tree(paths.base(d), paths.lnp(d))


def main():
    """Extract all components, in the required order."""
    print('\nExtracting components...')
    if os.path.isdir('build'):
        shutil.rmtree('build')
    extract_everything()
    add_lnp_dirs()
