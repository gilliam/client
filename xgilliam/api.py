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

import json
from urlparse import urljoin

from xgilliam.util import urlchild


class BuilderAPI(object):
    """Client API for the build server."""

    def __init__(self, endpoint, requests):
        self.endpoint = urljoin(endpoint, '/build')
        self.requests = requests

    def deploy(self, input_file, app, commit, text):
        """Deploy a new release via the build server."""
        params = {'app': app, 'commit': commit, 'text': text}
        headers = {'Content-Type': 'application/octet-stream'}
        response = self.requests.post(self.endpoint,
            data=input_file, params=params, stream=True,
            headers=headers)
        response.raise_for_status()
        return response.iter_content()


class SchedulerAPI(object):
    """Abstraction that provides functions to talk to the orchestrator
    using its REST API.
    """

    def __init__(self, endpoint, requests):
        self.endpoint = endpoint
        self.requests = requests

    def app(self, app):
        """Return the current app."""
        return self._get_json(urlchild(self.endpoint, 'app', app))

    def create_app(self, name, text):
        """Create a new app with the given name."""
        request = {'name': name, 'text': text}
        try:
            response = self.requests.post(urlchild(self.endpoint, 'app'),
                                          data=json.dumps(request))
            response.raise_for_status()
        except:
            raise
        else:
            return response.json()

    def create_release(self, app, text, build, image, pstable, app_config):
        """Create a new release."""
        try:
            request = {'text': text, 'build': build, 'image': image,
                       'pstable': pstable, 'config': app_config}
            response = self.requests.post(urlchild(self.endpoint,
                                                   'app', app, 'release'),
                                          data=json.dumps(request))
            response.raise_for_status()
        except:
            raise
        else:
            return response.json()

    def set_scale(self, app, version, scale):
        """Set scale values."""
        self._put_json(scale, self.endpoint, 'app', app,
                       'release', version, 'scale')

    def releases(self, app):
        """Iterate over releases."""
        url = urlchild(self.endpoint, 'app', app, 'release')
        while True:
            response = self._get_json(url)
            for item in response['items']:
                yield item
            if not response['links'].get('next'):
                break
            url = urljoin(url, response['links']['next'])

    def release(self, app, version=None):
        """Get a specific release or the latest release."""
        if version is None:
            releases = list(self.releases(app))
            return releases[0] if releases else None
        else:
            url = urlchild(self.endpoint, 'app', app, 'release', version)
            return self._get_json(url)

    def procs(self, app):
        url = urlchild(self.endpoint, 'app', app, 'proc')
        while True:
            response = self._get_json(url)
            for item in response['items']:
                yield item
            if not response['links'].get('next'):
                break
            url = urljoin(url, response['links']['next'])

    def restart_proc(self, app, proc_name):
        self._interact('delete', self.endpoint, 'app', app, 'proc', proc_name)

    def _interact(self, method, *parts, **kwargs):
        try:
            callable = getattr(self.requests, method)
            response = callable(urlchild(*parts), **kwargs)
            response.raise_for_status()
        except:
            raise
        else:
            if int(response.headers['content-length']):
                return response.json()
            else:
                return {}

    def _get_json(self, *parts):
        try:
            response = self.requests.get(urlchild(*parts))
            response.raise_for_status()
        except:
            raise
        else:
            return response.json()

    def _put_json(self, data, *parts):
        """Store data using a PUT request."""
        try:
            response = self.requests.put(urlchild(*parts),
                                         data=json.dumps(data))
            response.raise_for_status()
        except:
            raise
