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

from .. import scheduler


class Service(object):
    """Service for custom code (ie the business logic)."""

    IMAGE = 'gilliam/etcd'
    PORTS = [4001, 7001]

    def __init__(self, name, defn):
        self.name = name
        self.defn = defn

    def build(self, config, quiet):
        """Build the service and return its release definition."""
        return scheduler.make_service(self.IMAGE, None, self.PORTS)
