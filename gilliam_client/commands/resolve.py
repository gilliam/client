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

from gilliam.service_registry import Resolver


class Command(object):
    """Scale up a release."""

    synopsis = 'Scale up a release'

    def __init__(self, parser):
        parser.add_argument('host')
        parser.add_argument('port', default=80, type=int)

    def handle(self, config, options):
        """Handle the command."""
        resolver = Resolver(config.service_registry)
        host, port = resolver.resolve_host_port(options.host, options.port)
        print "%s %d" % (host, port)
