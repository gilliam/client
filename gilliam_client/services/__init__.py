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


def _iter():
    for fn in os.listdir(os.path.dirname(__file__)):
        if not fn.endswith('.py'):
            continue
        if fn in ('__init__.py',):
            continue
        mn, pyext = fn.split('.', 1)
        yield mn


def _import_service(mn):
    m = __import__('%s.%s' % (__name__, mn), {}, {}, ['Service'], 0)
    return m.Service


def detect(name, defn):
    """Try to detect a service from a name and/or definition."""
    type = defn.get('type')
    if type is not None:
        return load(type)

    if name[0] == '_':
        name = name[1:]

    services = list(_iter())
    if name in services:
        return load(name)

    if 'script' in defn:
        return load('custom')


def load(name):
    """Load all commands."""
    return _import_service(name)
