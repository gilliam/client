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

from ..config import FormationConfig

class Command(object):
    """Create formation."""

    synopsis = "create new formation"

    def __init__(self, parser):
        parser.add_argument('formation')
        parser.add_argument('-d', '--project-dir', metavar="DIR",
                            dest="project_dir")

    def handle(self, config, options):
        """Handle the command."""
        if options.project_dir:
            config.project_dir = options.project_dir
        if config.project_dir is None:
            sys.exit("cannot find project directory")

        scheduler = config.scheduler()
        formation = scheduler.create_formation(options.formation)

        form_config = FormationConfig.make(config.project_dir)
        form_config.formation = formation['name']
        if options.stage:
            form_config.stage = options.stage
