#!/usr/bin/env python3
"""Prepare a release of PeridexisErrant's Starter Pack for Dwarf Fortress.

Downloads and checks versions, assembles components, checks configuration,
and prepares everything for upload.

This code is highly specific to my pack - it's released under the GPL3,
but don't expect it to be particularly reusable.
"""

from starterpack import build, component, configure, dist

if __name__ == '__main__':
    component.report()
    component.download_files()
    build.build_all()
    configure.configure_all()
    dist.make()
