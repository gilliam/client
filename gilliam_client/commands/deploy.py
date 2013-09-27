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

import os
import sys
import time
import yaml

from .. import build, util


class Command(object):
    """Scale up a release."""

    synopsis = 'Build a release and migrate to it'

    def __init__(self, parser):
        parser.add_argument('--author', default=None)
        parser.add_argument('-m', '--message')
        parser.add_argument('--rate', dest='rate')

    def handle(self, config, options):
        """Handle the command."""
        if not config.formation:
            sys.exit("no formation; specify using -f")

        rate = util.parse_rate(options.rate)
        defn = self._read_defn(config)
        scheduler = config.scheduler()
        name = build.release(config, scheduler,
                             build.create_services(defn),
                             author=options.author,
                             message=options.message,
                             quiet=options.quiet)
        if not options.quiet:
            print "released %s" % (name,)
        build.migrate(config, scheduler, name, rate)

    def _read_defn(self, config):
        if not config.rootdir:
            sys.exit("cannot find a gilliam.yml file")
        with open(os.path.join(config.rootdir, 'gilliam.yml')) as fp:
            return yaml.load(fp)
