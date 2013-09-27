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
import yaml
import sys

_QUIET = [('name', 35, str)]
_NORMAL = [('name', 35, str), ('release', 7, str), ('state', 9, str)]
_VERBOSE = [('name', 35, str), ('release', 7, str), ('state', 9, str),
            ('assigned_to', 25, str), ('image', 25, str),
            ('command', 25, str)]


def _fmt(spec, data):
    """Format C{data} according to C{spec}."""
    result = []
    for i, (field, width, fmter) in enumerate(spec):
        last = (len(spec) - 1) == i
        value = fmter(data.get(field, ''))
        result.append('%-*s' % (0 if last else width, value))
    return ' '.join(result)


def _header(spec):
    result = []
    for (field, width, fmter) in spec:
        result.append('-' * width)
    return ' '.join(result)


class Command(object):
    """Display running instances."""

    synopsis = "show instances"

    def __init__(self, parser):
        parser.add_argument('-v', '--verbose', dest="verbose",
                            action="store_true")

    def _header(self, spec):
        if os.isatty(sys.stdout.fileno()):
            print _fmt(spec, {n: n for (n, w, f) in spec})
            print _header(spec)

    def handle(self, config, options):
        """Handle the command."""
        if not config.formation:
            sys.exit("no formation; specify using -f")
        
        if options.quiet:
            spec = _QUIET
        elif options.verbose:
            spec = _VERBOSE
        else:
            spec = _NORMAL

        if not options.quiet:
            self._header(spec)

        scheduler = config.scheduler()
        for instance in scheduler.instances(config.formation):
            print _fmt(spec, instance)
