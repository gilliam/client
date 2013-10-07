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
import yaml

from ..manifest import ProjectManifest
from .. import build


class Command(object):
    """Deploy a new release."""

    synopsis = 'Deploy a new release of the formation'

    def __init__(self, parser):
        parser.add_argument('--author', default=None)
        parser.add_argument('-m', '--message')

    def handle(self, config, options):
        """Handle the command."""
        if not config.project_dir:
            sys.exit("cannot find a gilliam.yml file")
        if not config.formation:
            sys.exit("no formation; specify using -f")

        manifest = ProjectManifest.load(config.project_dir)
        name = build.release(config, config.scheduler(),
                             build.create_services(manifest.services),
                             author=options.author,
                             message=options.message,
                             quiet=options.quiet)
        if not options.quiet:
            print "released", name
        else:
            print name
