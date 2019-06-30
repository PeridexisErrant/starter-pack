"""Unpack downloaded files to the appropriate place.

This module is about as generic as it can usefully be, pushing the special
cases back into build.py
"""

import concurrent.futures
from distutils.dir_util import copy_tree
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import zipfile

from . import component
from . import paths


class UnixAwareZipFile(zipfile.ZipFile):
    """A ZipFile subclass aware of how to extract UNIX file permissions."""
    @staticmethod
    def get_mode(info):
        """Returns the file mode that should be restored, or 0 if unknown."""
        # Values below are from the "version made by" documentation at
        # https://pkware.cachefly.net/webdocs/casestudies/APPNOTE.TXT
        unix, macos = 3, 19
        if info.create_system in (unix, macos):
            return (info.external_attr >> 16) & 0o777
        return 0

    def _extract_member(self, member, targetpath, pwd):
        # Based on internal implementation details of ZipFile, based on
        # https://github.com/python/cpython/blob/3.7/Lib/zipfile.py
        if not isinstance(member, zipfile.ZipInfo):
            member = self.getinfo(member)
        targetpath = super()._extract_member(member, targetpath, pwd)
        mode = UnixAwareZipFile.get_mode(member)
        if mode != 0:
            try:
                os.chmod(targetpath, mode)
            except OSError:
                print('Failed to correct mode of', targetpath)
                raise
        return targetpath


def _copyfile(src, dest, zipinfo=None):
    """Copy the source file path or object to the dest path, creating dirs."""
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if isinstance(src, str):
        if os.path.isfile(src):
            shutil.copy2(src, dest)
        elif os.path.isdir(src):
            copy_tree(src, dest)
        else:
            raise IOError('Unexpected file type for %s', src)
    elif isinstance(src, zipfile.ZipExtFile):
        with open(dest, 'wb') as out:
            shutil.copyfileobj(src, out)
        if zipinfo:
            mode = UnixAwareZipFile.get_mode(zipinfo)
            if mode != 0:
                try:
                    chmod(dest, mode)
                except OSError:
                    print('Failed to correct mode of', targetpath)
                    raise
    else:
        raise NotImplementedException('Unexpected source type')


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

    if path_pairs is not None or filename[-4:] in ('.exe', '.jar') \
            or not zipfile.is_zipfile(filename):
        # ensures consistent handling for path_pairs
        return nonzip_extract(filename, target_dir, path_pairs)
    # More complex, but faster for zips to do it this way
    with zipfile.ZipFile(filename) as zf:
        files = dict(a for a in zip(zf.namelist(), zf.infolist())
                     if not a[0].endswith('/'))
        prefix = os.path.commonpath(list(files)) if len(files) > 1 else ''
        for name, info in files.items():
            out = os.path.join(target_dir, os.path.relpath(name, prefix))
            _copyfile(zf.open(info), out, zipinfo=info)


def nonzip_extract(filename, target_dir=None, path_pairs=None):
    """An alternative to `unzip_to`, for non-zip archives.

    Extract to tempdir, copy files to destination/path_pairs, remove tempdir.

    Involves a lot of shelling out, as Python's `tarfile` cannot open
    the .tar.bz2 archived DF releases (complicated header issue).
    macOS disk images (.dmg) are also unsupported by Python.
    """
    if filename.endswith('.exe') and paths.HOST_OS == 'win' \
            or filename.endswith('.jar'):
        _copyfile(filename,
                  os.path.join(target_dir, os.path.basename(filename)))
        return True

    with tempfile.TemporaryDirectory() as tmpdir:
        if not unpack_anything(filename, tmpdir):
            raise RuntimeError('Could not extract file {}'.format(filename))
        # Copy from tempdir to destination
        files = [os.path.join(root, f)
                 for root, _, files in os.walk(tmpdir) for f in files]
        prefix = os.path.commonpath(files) if len(files) > 1 else ''
        # BAD HACK: It's an unsafe assumption (made above) that the common
        # path should always be stripped.
        if filename.endswith('.dmg') and 'Legends Browser' in target_dir:
            prefix = ''
        if target_dir:
            copy_tree(os.path.join(tmpdir, prefix), target_dir)
        else:
            for inpath, outpath in path_pairs:
                if outpath.endswith('/'):
                    outpath += os.path.basename(inpath)
                if os.path.exists(os.path.join(tmpdir, prefix, inpath)):
                    _copyfile(os.path.join(tmpdir, prefix, inpath), outpath)
                else:
                    print('WARNING:  "{}" not found in "{}"'.format(
                          inpath, os.path.basename(filename)))
    return True


def unpack_dmg(filename, dest):
    """Extract a .dmg disk image on macOS into the dest dir."""
    assert filename.endswith('.dmg') and paths.HOST_OS == 'osx'
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            subprocess.check_call(['hdiutil', 'attach', '-quiet', '-readonly',
                                   '-nobrowse', '-mountpoint', tmpdir,
                                   filename])
        except subprocess.CalledProcessError:
            print('Failed to mount', filename, ' -- is it already mounted?')
            raise
        try:
            copy_tree(tmpdir, dest, preserve_symlinks=True)
        finally:
            subprocess.check_call(['hdiutil', 'detach', '-quiet', tmpdir])



def unpack_anything(filename, tmpdir):
    """Extract practically any archive format from src file to dest dir."""
    if filename.endswith('.dmg') and paths.HOST_OS == 'osx':
        unpack_dmg(filename, tmpdir)
        return True
    elif zipfile.is_zipfile(filename):
        # zip files *can* include information about UNIX file modes, but Python
        # does not extract them. Skip using zipfile and just shell out to the
        # command line.
        UnixAwareZipFile(filename).extractall(tmpdir)
        return True
    elif any(filename.endswith('.tar.' + ext) for ext in ('bz2', 'xz', 'gz'))\
            or tarfile.is_tarfile(filename):
        tarfile.open(filename).extractall(tmpdir)
        return True
    elif filename.endswith('.rar'):
        try:
            import rarfile
        except ImportError:
            print('ERROR: .rar not supported; `pip install rarfile` and retry')
            return False
        rarfile.RarFile(filename).extractall(tmpdir)
        return True
    elif filename.endswith('.7z') or filename.endswith('.7zip'):
        exe = '7z'
        if sys.platform in ('win32', 'cygwin'):
            exe = r'C:\Program Files\7-Zip\7z.exe'
            if not os.path.isfile(exe):
                exe = exe.replace('Program Files', 'Program Files (x86)')
            exe = '"{}"'.format(exe)
        args = '{} x "{}" -o"{}"'.format(exe, filename, tmpdir)
        try:
            subprocess.run(args, check=True, stdout=subprocess.DEVNULL)
            return True
        except subprocess.CalledProcessError as e:
            print('ERROR: failed to extract {}, install 7z'.format(filename))
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
        name, seen = comp.name, []
        while name in after:
            seen.append(name)
            name = after.get(name)
            if name in seen:
                raise ValueError('Cyclic "install_after" config detected: ' +
                                 ' -> '.join(seen + [name]))
        return len(seen), os.path.getsize(comp.path)

    queue = list(component.ALL.values()) + [
        component.ALL['Dwarf Fortress']._replace(name=path, extract_to=path)
        for path in ('curr_baseline', 'graphics/ASCII')]
    queue.sort(key=q_key, reverse=True)
    with concurrent.futures.ProcessPoolExecutor(8) as pool:
        futures = dict()
        while queue:
            while sum(f.running() for f in futures.values()) < 8:
                for idx, comp in enumerate(queue):
                    aft = futures.get(comp.install_after)
                    # Even if it's highest-priority, wait for parent job(s)
                    if aft is None or aft.done():
                        futures[comp.name] = extract_comp(pool, queue.pop(idx))
                        break  # reset index or we might pop the wrong item
                else:
                    break  # if there was nothing eligible to extract, sleep
            time.sleep(0.01)
    failed = [k for k, v in futures.items() if v.exception() is not None]
    for key in failed:
        comp = component.ALL.pop(key, None)
        for lst in (component.FILES, component.GRAPHICS, component.UTILITIES):
            if comp in lst:
                lst.remove(comp)
    if failed:
        print('ERROR:  Could not extract: ' + ', '.join(failed))


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
