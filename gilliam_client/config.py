
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
from functools import wraps, partial
import os.path
import os

from gilliam import (BuilderClient, ExecutorClient,
                     SchedulerClient)
import requests

from . import util


def _resolve(registry):
    def decorator(fn):
        @wraps(fn)
        def wrapped(url, *args, **kw):
            return fn(registry.resolve(url), *args, **kw)
        return wrapped
    return decorator


def _make_http_adapter(registry, original):
    decorator = _resolve(registry)
    for mn in ('get', 'post', 'put', 'delete'):
        setattr(original, mn, decorator(getattr(original, mn)))
    return original


class Config(object):
    rootdir = None
    formation = None
    repository = None

    def __init__(self, registry, formation):
        """Initialize configuration based on environment."""
        self._setup_rootdir()
        self._setup_repository()
        self.formation = formation
        self.httpclient = _make_http_adapter(registry, requests)
        self.scheduler = partial(SchedulerClient, self.httpclient)
        self.executor = partial(ExecutorClient, self.httpclient)
        self.builder = partial(BuilderClient, self.httpclient)

    def _setup_rootdir(self):
        self.rootdir = util.find_rootdir()

    def _setup_repository(self):
        registry = os.getenv('GILLIAM_REGISTRY_DOMAIN', None)
        repository = os.getenv('GILLIAM_REGISTRY_USER',
                               getpass.getuser())
        if registry:
            assert ('.' in registry or ':' in registry)
            self.repository = '%s/%s' % (registry, repository)
        else:
            self.repository = repository
