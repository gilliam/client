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

from requests.exceptions import HTTPError

from . import errors


def make_service(image, command, ports):
    return {
        'image': image, 'command': command,
        'ports': ports, 'options': {}
        }


class Scheduler(object):
    """Client for the scheduler API."""

    def __init__(self, httpclient):
        self.httpclient = httpclient

    def _url(self, fmt, *args):
        path = fmt % args
        return 'http://api.scheduler.service/%s' % (path,)

    def releases(self, formation):
        url = self._url('formation/%s/release', formation)
        return util.traverse_collection(self.httpclient, url)

    def create_formation(self, formation):
        """Try to create a formation with the given name."""
        try:
            request = {'name': formation}
            response = self.httpclient.post(
                self._url('formation'), data=json.dumps(request))
            response.raise_for_status()
        except HTTPError, err:
            errors.convert_error(response)
            raise
        else:
            return response.json()

    def create_release(self, formation, name, author, message,
                       services):
        request = {'name': name, 'author': author, 'message': message,
                   'services': services}
        try:
            response = self.httpclient.post(
                self._url('formation/%s/release', formation),
                data=json.dumps(request))
            response.raise_for_status()
        except HTTPError, err:
            errors.convert_error(response)
            raise
        else:
            return response.json()

    def scale(self, formation, release, scales):
        try:
            request = {'scales': scales}
            response = self.httpclient.post(
                self._url('formation/%s/release/%s/scale',
                          formation, release),
                data=json.dumps(request))
            response.raise_for_status()
        except HTTPError, err:
            errors.convert_error(response)
            raise
        else:
            return response.json()

    def spawn(self, formation, release, image, command,
              env, ports, assigned_to=None):
        try:
            request = {
                'release': release, 'image': image, 'command': command,
                'env': env, 'ports': ports, 'assigned_to': assigned_to
                }
            response = self.httpclient.post(
                self._url('formation/%s/instance', formation),
                data=json.dumps(request))
            response.raise_for_status()
        except HTTPError, err:
            errors.convert_error(response)
            raise
        else:
            return response.json()
