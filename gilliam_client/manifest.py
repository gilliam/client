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


class ProjectManifest(object):
    """The project manifest file `gilliam.yml` lives in your project
    root directory.  The manifest describes your project in relations
    to Gilliam.

    """

    def __init__(self, services):
        self.services = services

    @classmethod
    def load(cls, dir):
        """Read manifest that lives in directory `dir`.

        :returns: The manifest object.
        :raises: OSError, IOError.
        """
        with open(os.path.join(dir, 'gilliam.yml')) as fp:
            defn = yaml.load(fp)
        return cls(defn)
