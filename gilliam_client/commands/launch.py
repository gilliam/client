# Copyright 2013 Johan Rydberg.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import yaml
from urllib import urlopen
import sys

from .. import errors


# Name of the initial release.
_INITIAL_RELEASE_NAME = '1'


class Command(object):
    """Launch a new formation from a release manifest."""

    synopsis = 'Launch a formation from a release manifest'

    def __init__(self, parser):
        parser.add_argument('manifest', help='release manifest')
        parser.add_argument('--scale', help='scale up the formation',
                            dest='scale', action='store_true')
        parser.add_argument('--create', action='store_true')
        
    def handle(self, config, options):
        """Handle the command."""
        release = self._read_release(options.manifest)
        scheduler = config.scheduler()
        if options.create:
            try:
                scheduler.create_formation(config.formation)
            except errors.ConflictError:
                sys.exit("%s: formation already exists" % (
                        options.formation,))
        else:
            release = scheduler.create_release(
                config.formation, _INITIAL_RELEASE_NAME,
                release.get('author', 'unknown'),
                release.get('message', ''),
                release.get('services', {}))
            print "CREATED", release
        if options.scale:
            self._scale(scheduler, options.formation,
                        release['services'].keys())

    def _read_release(self, fn):
        """Read release manifest and return it as a python C{dict}."""
        if fn.startswith("http://") or fn.startswith("https://"):
            with urlopen(fn) as fp:
                return json.load(fp)
        elif fn == '-':
            return yaml.load(sys.stdin)
        else:
            with open(fn) as fp:
                return yaml.load(fp)

    def _scale(self, scheduler, formation, release, names):
        scales = {name: 1 for name in names}
        while True:
            done = not scheduler.scale(formation, release, scales)
            if done:
                break
