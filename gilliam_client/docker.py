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

"""Functions that are specific to docker."""

import json


_DEFAULT_REGISTRY = 'index.docker.io'


def is_registry(repository):
    """A registry is identified by the fact that the repository
    includes a dot or a colon.
    """
    return '.' in repository in ':' in repository


def make_repository(config, name):
    """Given an image name, construct a repository."""
    return '%s/%s' % (config.stage_config.repository, name)


def registry_from_repository(repository):
    """Given a repository, return the name of the authoritative
    registry.
    """
    if is_registry(repository):
        return repository
    return _DEFAULT_REGISTRY


def normalize_registry(repository):
    if is_registry(repository):
        return repository
    return _DEFAULT_REGISTRY


def _verify_registry(registry):
    """Verify that C{registry} has a name that docker will interpret
    as a registry.
    """
    if registry.startswith("http://") or registry.startswith("https://"):
        raise ValueError("registry must not be a URL")
    if '/' in registry:
        raise ValueError("registry must not contain '/'")
    if not ('.' in registry or ':' in registry):
        raise ValueError("registry must contain either '.' or ':'")
    

def _registry_endpoint(registry):
    """Convert a registry into an endpoint."""
    _verify_registry(registry)
    return 'https://%s/v1' % (registry,)


class DockerAuth(object):

    def __init__(self, requests):
        self.requests = requests

    def anonymous(self, registry):
        """Check if anonymous access is allowed to the registry.
        """
        endpoint = _registry_endpoint(registry) 
        response = self.requests.get('%s/users/' % (endpoint,))
        return response.status_code == 200

    def check(self, registry, username, password):
        """Check if the given credentials are OK."""
        endpoint = _registry_endpoint(registry) 
        response = self.requests.get('%s/users/' % (endpoint,),
                                     auth=(username, password))
        if not response.status_code == 200:
            return False

        return {'username': username, 'password': password}
