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

from .. import scheduler


@contextmanager
def _stream_tarball(dir):
    popen = subprocess.Popen(['tar', '-c', 
                              '--exclude-vcs',
                              '--exclude-backups',
                              '-C', dir, '.'],
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


def _filter_files(filenames):
    return [filename for filename in filenames
            for pattern in _EXCLUDE_FILES
            if not fnmatch(filename, pattern)]


def _compute_tag(dir):
    """Compute tag."""
    h = hashlib.md5()
    for (dirpath, dirnames, filenames) in os.walk(dir):
        dirnames[:] = [dirname for dirname in dirnames
                       if dirname not in _EXCLUDE_DIRS]
        h.update(dirpath)
        for filename in _filter_files(filenames):
            h.update(filename)
            path = os.path.join(dir, dirpath, filename)
            with open(path, 'r') as fp:
                for data in iter(partial(fp.read, 4096), ''):
                    h.update(data)
    return h.hexdigest()

        
class Service(object):
    """Service for custom code (ie the business logic)."""

    def __init__(self, name, defn):
        self.name = name
        self.defn = defn

    def build(self, config, quiet):
        """Build the service and return its release definition."""
        builder = config.builder()
        approot = os.path.join(config.rootdir, self.defn.get('approot', '.'))

        repository = '%s/%s-%s' % (config.repository,
                                   config.formation,
                                   self.name)
        tag = _compute_tag(approot)

        if not quiet:
            print "[%s] start building ..." % (self.name,)

        with _stream_tarball(approot) as process:
            exit_code = builder.build(repository, tag, process.stdout,
                                      sys.stdout)

        if exit_code:
            sys.exit("[%s] build failed: %d" % (self.name, exit_code,))
        else:
            if not quiet:
                print "[%s] done!" % (self.name,)

        image = '%s:%s' % (repository, tag)
        return scheduler.make_service(image, self.defn.get('script'),
            self.defn.get('ports', []))
