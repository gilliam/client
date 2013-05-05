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

import os.path
import os
import sys

import requests

from xgilliam.api import SchedulerAPI, BuilderAPI


class Config(object):
    """Wraps our configuration."""

    ATTACH = '.gilliam.app'

    def __init__(self, requests=requests):
        self._attach = None
        self._app = None
        self._requests = requests

    def _read_attach(self):
        if self._attach is None:
            if not os.path.exists(self.ATTACH):
                raise RuntimeError("Not attached to an app")
            with open(self.ATTACH) as fp:
                self._attach = fp.read().strip()
        return self._attach

    def _read_app(self):
        return self._read_attach()

    def write_app(self, app):
        with open(self.ATTACH, 'wb') as fp:
            fp.write(app)
        self._app = app

    @property
    def app(self):
        if self._app is None:
            self._app = self._read_app()
        return self._app

    @app.setter
    def app(self, app):
        self._app = app

    def scheduler(self):
        return SchedulerAPI(self._scheduler_url(), self._requests)

    def builder(self):
        return BuilderAPI(self._builder_url(), self._requests)

    def _builder_url(self):
        if not "GILLIAM_BUILDER" in os.environ:
            sys.exit("GILLIAM_BUILDER env variable not set")
        return os.getenv("GILLIAM_BUILDER")

    def _scheduler_url(self):
        if not "GILLIAM_SCHEDULER" in os.environ:
            sys.exit("GILLIAM_SCHEDULER env variable not set")
        return os.getenv("GILLIAM_SCHEDULER")
