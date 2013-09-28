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

import json
from urllib import urlopen
import sys

from .. import errors, util, port_spec


class Command(object):
    """Launch a new formation from a release manifest."""

    synopsis = 'Launch a formation from a release manifest'

    def __init__(self, parser):
        parser.add_argument('service', help='service template')
        parser.add_argument('-r', '--release', metavar="NAME",
                            help="release")
        parser.add_argument('--assigned-to', metavar="NAME", dest="assigned_to",
                            help="assign instance to NAME")
        parser.add_argument('-p', '--port', action='append',
                            dest="ports", default=[], help="port mapping")
        parser.add_argument('--require', action='append',
                            default=[], dest="requirements")
        parser.add_argument('--rank', default=None)
        
    def _find_release(self, config, scheduler, name):
        for release in scheduler.releases(config.formation):
            if release['name'] == name:
                return release
        return None

    def _find_service(self, release, name):
        service = release['services'].get(name)
        if service is None:
            sys.exit("%s: no such service" % (name,))
        return (service['image'], service['command'],
                service.get('env', {}),
                service.get('ports', []))

    def _merge_ports(self, ports, option_ports):
        port_specs = {ps.private: ps for ps in (
                _parse_port_spec(str(ps)) for ps in ports)}
        for spec in option_ports:
            port_spec = _parse_port_spec(spec)
            port_specs[port_spec.private] = port_spec
        return [_fmt_port_spec(ps) for ps in port_specs.values()]
    
    def handle(self, config, options):
        """Handle the command."""
        if not config.formation:
            sys.exit("cannot detect formation")
        scheduler = config.scheduler()

        if not options.release:
            release = util.last(scheduler.releases(config.formation))
        else:
            release = self._find_release(config, scheduler,
                                         options.release)
        if release is None:
            sys.exit("no release in formation")

        placement = {'requirements': options.requirements,
                     'rank': options.rank}

        image, command, env, ports = self._find_service(
            release, options.service)
        ports = port_spec.merge_port_specs(ports, options.ports)

        inst = scheduler.spawn(config.formation, options.service,
                               release['name'], image, command, env,
                               ports, options.assigned_to,
                               options.requirements, options.rank)
        if not options.quiet:
            print inst['name']
