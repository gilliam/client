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
import getpass

from gilliam_client.services import detect
from gilliam_client.errors import ConflictError
import yaml


def last(it, default=None):
    for default in it:
        pass
    return default


class Command(object):
    """Deploy a new release."""

    synopsis = 'Deploy a new release of the formation'

    def __init__(self, parser):
        parser.add_argument('--author', default=getpass.getuser())
        parser.add_argument('-m', '--message')

    def _create_services(self, defn):
        services = {}

        for name, svcdef in defn.items():
            cls = detect(name, svcdef)
            if cls is None:
                sys.exit("cannot detect service type for %s" % (
                        name,))

            services[name] = cls(name, svcdef)

        return services

    def _build_services(self, config, options, services):
        release = {}
        for name, service in services.items():
            release[name] = service.build(config, options.quiet)
        return release

    def _name_release(self, current):
        return (int(current['name']) + 1 if current is not None else 1)

    def _merge_releases(self, current, services):
        """Merge services."""
        if current:
            base = current['services']
            for name, defn in services.items():
                if name in base:
                    env = base[name].get('env', {})
                    env.update(defn.get('env', {}))
                    defn['env'] = env
        return services

    def _release(self, config, options, services):
        scheduler = config.scheduler()
        built_services = self._build_services(config, options,
                                              services)
        while True:
            current = next(scheduler.releases(config.formation))
            try:
                response = config.scheduler().create_release(
                    config.formation, self._name_release(current),
                    options.author or 'unknown',
                    options.message or '',
                    self._merge_releases(current, built_services))
            except ConflictError:
                continue
            else:
                return response['name']

    def handle(self, config, options):
        """Handle the command."""
        if not config.rootdir:
            sys.exit("cannot find a gilliam.yml file")
        if not config.formation:
            sys.exit("no formation; specify using -f")
        with open(os.path.join(config.rootdir, 'gilliam.yml')) as fp:
            defn = yaml.load(fp)
        name = self._release(config, options, self._create_services(defn))
        if not options.quiet:
            print "released", name
        else:
            print name
