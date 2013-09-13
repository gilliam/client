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

import argparse
import os
import sys
import time

from gilliam.service_registry import ServiceRegistryClient

from .config import Config
from . import commands


SERVICE_REGISTRY_ENVVAR_NAME = 'GILLIAM_SERVICE_REGISTRY_NODES'


def main():
    """Main entry point for the command-line tool."""
    parser = argparse.ArgumentParser('gilliam-cli')
    parser.add_argument('-f', metavar='NAME', dest='formation',
                        help='Formation the subcommand applies to')
    parser.add_argument('-q', '--quiet', dest='quiet',
                        action='store_true', default=False)
    cmds = dict(_init_commands(parser))

    options = parser.parse_args()
    config = Config(_service_registry(), options.formation)

    cmd = cmds[options.cmd]
    cmd.handle(config, options)

    
def _init_commands(parser):
    """Initialize the commands."""
    subparsers = parser.add_subparsers(title='subcommands',
                                       dest='cmd')
    for name, cls in commands.load():
        cmd = cls(subparsers.add_parser(name, help=cls.synopsis,
                                        description=cls.__doc__))
        yield name, cmd


def _service_registry():
    """Return a service registry based on the information in the
    environment.
    """
    nodes = os.getenv(SERVICE_REGISTRY_ENVVAR_NAME)
    if not nodes:
        sys.exit("envvar %s not set" % (SERVICE_REGISTRY_ENVVAR_NAME,))
    return ServiceRegistryClient(time, nodes.split(','))
