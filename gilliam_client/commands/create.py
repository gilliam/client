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


class Command(object):
    """Create formation."""

    synopsis = "create new formation"

    def __init__(self, parser):
        parser.add_argument('formation')

    def handle(self, config, options):
        """Handle the command."""
        if config.rootdir is None:
            config.rootdir = os.getcwd()

        scheduler = config.scheduler()
        formation = scheduler.create_formation(options.formation)
        
        path = os.path.join(config.rootdir, '.gilliam', 'formation')
        try:
            os.makedirs(os.path.dirname(path))
        except OSError:
            pass

        with open(path, 'w') as fp:
            fp.write(formation['name'])
