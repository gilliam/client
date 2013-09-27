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

from urlparse import urljoin
import os


def parse_rate(rate):
    """Parse rate and return number of seconds to pause between
    calls to C{scale}.
    """
    if not rate:
        return 0
    else:
        return 10


def find_rootdir(fn='gilliam.yml'):
    cwd = os.getcwd()
    while cwd != '/':
        if os.path.exists(os.path.join(cwd, fn)):
            return cwd
        cwd = os.path.realpath(os.path.join(cwd, '..'))
    return None


def traverse_collection(httpclient, url):
    """Traverse a collection, yielding every item."""
    while True:
        response = httpclient.get(url)
        collection = response.json()
        for item in collection['items']:
            yield item
        if not 'next' in collection['links']:
            break
        url = urljoin(url, collection['links']['next'])


def last(it, default=None):
    for default in it:
        pass
    return default
