#!/usr/bin/env python3
"""Prepare a release of PeridexisErrant's Starter Pack for Dwarf Fortress.

Downloads and checks versions, assembles components, checks configuration,
and prepares everything for upload.

This code is highly specific to my pack - it's released under the GPL3,
but don't expect it to be particularly reusable.
"""

import datetime

from starterpack import build, component, dist, extract

if __name__ == '__main__':
    print('The time is {} UTC\n'.format(
        str(datetime.datetime.utcnow()).split('.')[0]))
    for stage in (component, extract, build, dist):
        stage.main()
