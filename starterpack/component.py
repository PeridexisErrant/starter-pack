"""Sole interface module for config.yml

Offers a set of shared commands backed by minimal manual config.
"""

import json
import os
import yaml

from . import download
from . import paths


with open('config.yml') as ymlfile:
    YML = yaml.safe_load(ymlfile)


class ManualMetadata(download.AbstractMetadata):
    """Mock metadata API for locally configured components."""
    def json(self, identifier):
        for category in YML.values():
            if identifier in category:
                return category[identifier]

    def dl_link(self, identifier):
        return self.json(identifier)['dl_link']

    def filename(self, identifier):
        return os.path.basename(self.dl_link(identifier))


class Component(object):
    """Represent a downloadable component, with metadata."""
    #pylint:disable=too-many-instance-attributes,too-few-public-methods

    def __init__(self, category, item):
        self.config = YML[category][item]
        self.category = category
        self.name = item
        self.bay12 = str(self.config.get('bay12', 126076))
        self.thread = ('http://www.bay12forums.com/smf/index.php?topic=' +
                       self.bay12)
        self.ident = (self.name if self.config['host'] == 'manual'
                      else self.config['ident'])
        metadata = {'dffd': download.DFFDMetadata,
                    'github': download.GitHubMetadata,
                    'manual': ManualMetadata}[self.config['host']]()
        self.dl_link = metadata.dl_link(self.ident)
        self.filename = metadata.filename(self.ident)
        self.version = metadata.version(self.ident)
        self.path = paths.component(self.filename)

    def download(self):
        """Ensure that the given file is downloaded to the components dir."""
        if os.path.isfile(self.path):
            return False
        print('downloading {}...'.format(self.name))
        buf = download.download(self.dl_link)
        with open(self.path, 'wb') as f:
            f.write(buf)
        return True


__items = [(cat, item) for cat, vals in YML.items() for item in vals
           if cat not in {'comment', 'version'}]

COMPONENTS = tuple(Component(k, i) for k, i in __items)

ALL = {c.name: c for c in COMPONENTS}

UTILITIES = tuple(c for c in COMPONENTS if c.category == 'utilities')
GRAPHICS = tuple(c for c in COMPONENTS if c.category == 'graphics')
FILES = tuple(c for c in COMPONENTS if c.category == 'files')

for comp in COMPONENTS:
    print('{:25}{:15}{}'.format(comp.name, comp.version, comp.filename[:30]))

with open('_cached.json', 'w') as cachefile:
    json.dump(download.JSON_CACHE, cachefile, indent=4)
