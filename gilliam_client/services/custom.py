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
import logging
import os
import random
import sys
import subprocess
import time
import requests

from gilliam import errors

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


class LogFile(object):
    pending = ''

    def __init__(self, log, indent):
        self.log = log
        self.indent = indent

    def write(self, data):
        data = self.pending + data
        self.pending = ''
        lines = data.splitlines(True)
        if lines[-1][-1] != '\n':
            self.pending = lines.pop()
        for line in lines:
            self.log.info(self.indent + line[:-1])


class Service(object):
    """Service for custom code (ie the business logic)."""

    _CHUNK_SIZE = 1 * 1024 * 1024

    def __init__(self, name, defn):
        self.log = logging.getLogger('service.custom[{0}]'.format(name))
        self.name = name
        self.defn = defn
        self.time = time

    def _select_executor(self, config):
        alts = config.service_registry.query_formation('executor')
        alt = random.choice([d for (k, d) in alts])
        return config.executor('%s.api.executor.service' % (
                alt['instance'],))

    def build(self, config, push_images=True, **options):
        """Build the service and return its release definition.

        :param bool push_images: If True, check credentials against
            registry since the built image will be pushed.
        """
        self.executor = self._select_executor(config)
        builder = config.builder(self.executor)
        approot = os.path.join(config.project_dir, self.defn.get('approot', '.'))

        if push_images:
            self.credentials = self._check_credentials(config)

        image = '%s-%s' % (config.formation, self.name)
        self.repository = make_repository(config, image)
        self.tag = _compute_tag(approot)

        self.log.info("start building service '{0}' ...".format(self.name))
        with _stream_tarball(approot) as process:
            reader = iter(partial(process.stdout.read, self._CHUNK_SIZE), '')
            exit_code = builder.build(
                self.repository, self.tag, reader, LogFile(self.log, ' | '))

        if exit_code:
            sys.exit("[%s] build failed: %d" % (self.name, exit_code,))

        self.log.debug("build successful!")

        image = '%s:%s' % (self.repository, self.tag)
        return scheduler.make_service(image, self.defn.get('script'),
            self.defn.get('ports', []))

    def commit(self, config, push_images=True, **options):
        """Commit the build of the service."""
        if not push_images:
            return

        t0 = self.time.time()
        self.log.info("start pushing image {0}:".format(self.repository))
        try:
            CLEAR = '\033[K'
            try:
                for doc in self.executor.push_image(self.repository, self.credentials):
                    if not 'status' in doc:
                        sys.stdout.write("\n")
                    elif 'progress' in doc:
                        sys.stdout.write("\r{0}{1} [{2}]".format(
                                CLEAR, doc['status'], doc['progress']))
                    else:
                        sys.stdout.write("\r{0}{1}".format(CLEAR, doc['status']))
                    sys.stdout.flush()
            except errors.GilliamError:
                raise
        finally:
            sys.stdout.write("\n")
            t1 = self.time.time()
            self.log.info("done (time {0}s)".format(t1 - t0))

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

        if not cred:
            raise Exception("need to authenticate with %s" % (
                    registry,))

        authcfg = docker_auth.check(registry, cred.username,
                                    cred.password)
        if not authcfg:
            raise Exception("need to authenticate with %s" % (
                    registry,))

        return authcfg
