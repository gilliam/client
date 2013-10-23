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

from gilliam_client.services import detect
from gilliam_client.errors import ConflictError


def create_services(defn):
    services = {}
    for name, svcdef in defn.items():
        cls = detect(name, svcdef)
        if cls is None:
            sys.exit("cannot detect service type for %s" % (
                    name,))
        services[name] = cls(name, svcdef)
    return services


def _build_services(config, services, push_images):
    release = {}
    options = dict(push_images=push_images)
    for name, service in services.items():
        release[name] = service.build(config, **options)
    for name, service in services.items():
        service.commit(config, **options)
    return release


def _name_release(current):
    return str(int(current['name']) + 1 if current is not None else 1)


def merge_releases(current, services):
    """Merge services."""
    if current:
        base = current['services']
        for name, defn in services.items():
            if name in base:
                env = base[name].get('env', {})
                env.update(defn.get('env', {}))
                defn['env'] = env
    return services


def _last_release(config, scheduler):
    releases = list(scheduler.releases(config.formation))
    if not releases:
        return None
    releases.sort(key=lambda release: int(release['name']))
    return releases[-1]


def release(config, scheduler, services, author=None, message='',
            override_env=False, push_images=True):
    built_services = _build_services(config, services, push_images)
    while True:
        current = _last_release(config, scheduler)
        try:
            response = scheduler.create_release(
                config.formation, _name_release(current),
                author or getpass.getuser(), message,
                built_services if override_env else merge_releases(
                    current, built_services))
        except ConflictError:
            continue
        else:
            return response['name']


def migrate(config, scheduler, release, rate):
    while True:
        more = scheduler.migrate(config.formation, release)
        if not more:
            break
        else:
            time.sleep(rate)
