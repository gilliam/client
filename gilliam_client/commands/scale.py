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
import time


class Command(object):
    """Scale up a release."""

    synopsis = 'Scale up a release'

    def __init__(self, parser):
        parser.add_argument('release')
        parser.add_argument("scale", nargs='+')
        parser.add_argument('--rate', dest='rate')

    def _parse_rate(self, rate):
        """Parse rate and return number of seconds to pause between
        calls to C{scale}.
        """
        if not rate:
            return 0
        else:
            return 10

    def _parse_scale(self, scale):
        try:
            name, num = scale.split('=', 1)
            return name, int(num)
        except (TypeError, ValueError):
            sys.exit("%s: bad scale format" % (scale,))

    def _scale(self, config, release, scales, rate):
        scheduler = config.scheduler()
        while True:
            more = scheduler.scale(config.formation, release,
                                   scales)
            if not more:
                break
            else:
                time.sleep(rate)

    def handle(self, config, options):
        """Handle the command."""
        if not config.formation:
            sys.exit("no formation; specify using -f")
        scales = dict(self._parse_scale(scale) for scale in options.scale)
        rate = self._parse_rate(options.rate)
        self._scale(config, options.release, scales, rate)
