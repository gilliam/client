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


import getpass
import os
import sys
import time

import requests

from ..docker import DockerAuth, registry_from_repository


class Command(object):
    """\
    Authenticate with a image registry.

    It is possible to specify which registry to authenticate with
    using the `--registry` option.  If not given, authentication will
    be done against the default registry for the stage.
    """

    synopsis = 'Authenticate against a registry'

    def __init__(self, parser):
        parser.add_argument("-r", "--registry", metavar="REGISTRY")
        parser.add_argument("-u", "--username", metavar="USERNAME")
        parser.add_argument("-p", "--password", metavar="PASSWORD")
        self.docker_auth = DockerAuth(requests)

    def _credentials(self, options):
        if not options.username:
            default = getpass.getuser()
            options.username = raw_input('Username (%s): ' % (default,))
            if not options.username:
                options.username = default
        if not options.password:
            options.password = getpass.getpass()
        return options.username, options.password

    def handle(self, config, options):
        """Handle the command."""
        registry = options.registry
        if not registry:
            registry = registry_from_repository(
                config.stage_config.repository)

        print "Please enter credentials for %s:\n" % (registry,)
        username, password = self._credentials(options)

        if not self.docker_auth.check(registry, username, password):
            sys.exit("invalid username or password")

        with config.auth_config as ac:
            ac.store(registry, options.username, options.password)
