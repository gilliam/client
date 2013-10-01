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

"""
gilliam-cli route /builder/{tail:.*?} builder.service/{tail}
gilliam-cli route api.router.com/builder/{tail:.}
"""

import shortuuid

from .. import fmt


_SPEC = [('name', 22, str), ('domain', 20, str), ('path', 20, str),
         ('target', 25, str)]


class Command(object):
    """Set up a route via gateway."""


    synopsis = 'Set up a new REST route'

    def __init__(self, parser):
        parser.add_argument('-d', '--delete', action="store_true")
        parser.add_argument('route', nargs='?')
        parser.add_argument('target', nargs='?')

    def _parse_route(self, route):
        if ':' in route:
            domain, path = route.split(':', 1)
        else:
            domain, path = None, route
        return domain, path

    def _delete(self, router, config, options):
        try:
            router.delete(options.route)
        except:
            raise

    def _create(self, router, config, options):
        if not options.target:
            sys.exit("must specify route target")

        if not options.target.startswith('http://'):
            options.target = 'http://' + options.target

        domain, path = self._parse_route(options.route)
        route = router.create(shortuuid.uuid(), domain, path, options.target)
        print "route %s created" % (route['name'],)

    def _list(self, router, config, options):
        print fmt.fmt(_SPEC, {n: n for (n, w, t) in _SPEC})
        print fmt.header(_SPEC)
        for route in router.routes():
            print fmt.fmt(_SPEC, route)

    def handle(self, config, options):
        # Always assume that we're dealing with HTTP.
        router = config.router()

        if options.delete:
            self._delete(router, config, options)
        elif not options.route:
            self._list(router, config, options)
        else:
            self._create(router, config, options)
