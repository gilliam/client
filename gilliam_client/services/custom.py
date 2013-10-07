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

from contextlib import contextmanager
from functools import partial
from fnmatch import fnmatch
import hashlib
import json
import os
import sys
import subprocess
import requests

from ..docker import registry_from_repository, make_repository, DockerAuth
from .. import scheduler



@contextmanager
def _stream_tarball(dir):
    options = ['--exclude-vcs', '--exclude-backups']

    ignore = os.path.join(dir, '.gilliam/ignore')
    if os.path.exists(ignore):
        options.extend(['-X', ignore])

    popen = subprocess.Popen(['tar', '-c']
                             + options
                             + ['-C', dir, '.'],
                             bufsize=4096,
                             stdout=subprocess.PIPE)
    yield popen
    popen.wait()


def _stream_output(build, outfile):
    def _stream():
        build.attach(outfile)
    
    t = threading.Thread(target=_stream)
    t.daemon = True
    t.start()


_EXCLUDE_DIRS = ['CVS', 'RCS', 'SCCS', '.git',
                 '.svn', '.arch-ids', '{arch}',
                 '.bzr', '.hg', '_darcs']
_EXCLUDE_FILES = ['.gitignore', '.cvsignore',
                  '.hgignore', '.bzrignore',
                  'gilliam.yml', '.#*', '*~', '#*#']

def _filter(names, patterns):
    def it():
        for name in names:
            for pattern in patterns:
                if fnmatch(name, pattern) or name == pattern:
                    break
            else:
                yield name
    return list(it())


def read_ignore_patterns(dir, filename='.gilliam/ignore'):
    """Read content of the **ignore** file.  The file contains
    patterns, that if they match a file or directory, means that the
    subject should not be included in the data that will be sent to
    the build server.

    :param extras: a list of extra patterns.
    """
    path = os.path.join(dir, filename)
    if not os.path.exists(path):
        return []
    
    with open(path) as fp:
        return [line for line in fp
                if line and not line.startswith("#")]


def _compute_tag(dir):
    """Compute tag."""
    patterns = read_ignore_patterns(dir)
    patterns.extend(_EXCLUDE_DIRS)
    patterns.extend(_EXCLUDE_FILES)

    h = hashlib.md5()
    for (dirpath, dirnames, filenames) in os.walk(dir):
        dirnames[:] = _filter(dirnames, patterns)
        h.update(dirpath)
        for filename in _filter(filenames, patterns):
            h.update(filename)
            path = os.path.join(dir, dirpath, filename)
            with open(path, 'r') as fp:
                for data in iter(partial(fp.read, 4096), ''):
                    h.update(data)
    return h.hexdigest()

        
class Service(object):
    """Service for custom code (ie the business logic)."""

    _CHUNK_SIZE = 1 * 1024 * 1024

    def __init__(self, name, defn):
        self.name = name
        self.defn = defn

    def build(self, config, quiet, dry_run=True):
        """Build the service and return its release definition."""
        builder = config.builder()
        approot = os.path.join(config.project_dir, self.defn.get('approot', '.'))

        credentials = self._check_credentials(config)
        image = '%s-%s' % (config.formation, self.name)
        repository = make_repository(config, image)
        tag = _compute_tag(approot)

        if not quiet:
            print "[%s] start building ..." % (self.name,)

        with _stream_tarball(approot) as process:
            reader = iter(partial(process.stdout.read, self._CHUNK_SIZE), '')
            exit_code = builder.build(repository, tag, reader, sys.stdout)

        if exit_code:
            sys.exit("[%s] build failed: %d" % (self.name, exit_code,))
        else:
            if not quiet:
                print "[%s] build done! will start pushing ..." % (self.name,)
            

        image = '%s:%s' % (repository, tag)
        return scheduler.make_service(image, self.defn.get('script'),
            self.defn.get('ports', []))

    def _check_credentials(self, config):
        """Check that the user has authenticated with the
        registry/index that will hold the image.
        
        Return an access token that will be passed to the executor
        when it commits and pushes the image.
        """
        docker_auth = DockerAuth(requests)

        registry = registry_from_repository(config.stage_config.repository)
        cred = config.auth_config.get(registry)

        if docker_auth.anonymous(registry):
            return None
        elif cred:
            docker_creds = docker_auth.check(registry,
                                             cred.username,
                                             cred.password)
            if not docker_creds:
                raise Exception("need to authenticate with %s" % (
                        registry,))

            return docker_creds
        else:
            return None
