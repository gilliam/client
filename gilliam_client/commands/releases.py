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


def last(it, default=None):
    for default in it:
        pass
    return default


class Command(object):
    """Display releases."""

    synopsis = "list releases"

    def __init__(self, parser):
        parser.add_argument('--dump', metavar="NAME")

    def _header(self):
        if os.isatty(sys.stdout.fileno()):
            print "%-9s %-15s %s" % ("name", "author", "message")
            print "%-9s %-15s %s" % ("-" * 9, "-" * 15, "-" * 40)

    def _print(self, release, options):
        print "%-9s %-15s %s" % (release['name'], release.get(
                'author', 'unknown'), release.get('message', ''))

    def _dump(self, config, scheduler, name):
        for release in scheduler.releases(config.formation):
            if release['name'] == name:
                yaml.safe_dump(release, sys.stdout, encoding='utf-8', tags=None,
                          default_flow_style=False)
                return
        sys.exit("no such release")

    def handle(self, config, options):
        """Handle the command."""
        if not config.formation:
            sys.exit("no formation; specify using -f")

        scheduler = config.scheduler()

        if options.dump:
            return self._dump(config, scheduler, options.dump)

        self._header()
        for release in scheduler.releases(config.formation):
            self._print(release, options)
