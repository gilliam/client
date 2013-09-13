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

from fnmatch import fnmatch
import hashlib
import os
import json
import sys
import subprocess

from .. import scheduler


class Manifest(object):

    def __init__(self, files=None):
        if files is None:
            files = {}
        self.files = files

    @classmethod
    def read(cls, fn):
        with open(fn) as fp:
            return cls(json.read(fp))

    def write(self, fn):
        """Write the manifest to a file."""
        try:
            os.makedirs(os.path.dirname(fn))
        except OSError:
            pass
        with open(fn, 'w') as fp:
            fp.write(json.dumps(self.files, indent=2))

    def update(self, rootdir):
        patterns = self._read_ignore(rootdir)
        for dirpath, dirnames, filenames in os.walk(rootdir):
            for fn in filenames:
                if self._match_pattern(patterns, fn):
                    continue
                ffn = os.path.join(dirpath[len(rootdir):], fn)
                self.files[ffn] = self._compare(
                    self.files.get(ffn), os.path.join(dirpath, fn))

    def _read_ignore(self, rootdir):
        path = os.path.join(rootdir, '.gilliamignore')
        patterns = ['.git', '.gilliam']
        if os.path.exists(path):
            with open(path) as fp:
                for line in fp:
                    if not line or line.startswith("#"):
                        continue
                    patterns.append(line)
        return patterns

    def _match_pattern(self, patterns, fn):
        for pattern in patterns:
            if fnmatch(fn, pattern):
                return True
        return False

    def _compare(self, e, path):
        st = os.lstat(path)
        if stat.S_ISLNK(st.st_mode):
            return {
                'symlink': os.readlink(path),
                'mode': stat.S_IMODE(st.st_mode),
                }

        if e and 'mtime' in e:
            if os.path.getmtime(path) == e['mtime']:
                return e
        with open(path) as fp:
            h = hashlib.new('sha256')
            while True:
                data = fp.read()
                if not data:
                    break
                h.update(data)
            digest = h.hexdigest()
        return {'mtime': os.path.getmtime(path),
                'hash': digest,
                'mode': stat.S_IMODE(st.st_mode)}


def _read_or_create_manifest(fn):
    try:
        m = Manifest.read(path)
    except OSError:
        m = Manifest()
    return m

from contextlib import contextmanager

@contextmanager
def _stream_tarball(dir):
    popen = subprocess.Popen(['tar', '-cC', dir, '.'],
                             stdout=subprocess.PIPE)
    yield popen
    popen.wait()


def _stream_output(build, outfile):
    def _stream():
        build.attach(outfile)
    
    t = threading.Thread(target=_stream)
    t.daemon = True
    t.start()

        
class Service(object):
    """Service for custom code (ie the business logic)."""

    def __init__(self, name, defn):
        self.name = name
        self.defn = defn

    def _build_and_commit(self, config, repository):
        executor = config.executor()
        process = executor.run(config.formation, options.image, {}, options.command)
        self._attach(process)
        exit_code = process.wait()
        if not exit_code and options.repository:
            process.commit(options.repository)
        sys.exit(exit_code)

    def build(self, config, quiet):
        """Build the service and return its release definition."""
        builder = config.builder()
        approot = os.path.join(config.rootdir, self.defn.get('approot', '.'))
        repository = '%s/%s-%s' % (config.repository,
                                   config.formation,
                                   self.name)
        tag = 'xlatest'

        if not quiet:
            print "[%s] start building ..." % (self.name,)

        # with _stream_tarball(approot) as process:
        #     exit_code = builder.build(repository, tag, process.stdout,
        #                               sys.stdout)

        # if exit_code:
        #     sys.exit("[%s] build failed: %d" % (self.name, exit_code,))
        # else:
        #     if not quiet:
        #         print "[%s] done!" % (self.name,)

        image = '%s:%s' % (repository, tag)
        return scheduler.make_service(image, self.defn.get('script'),
            self.defn.get('ports', []))

    def _manifest_path(self, rootdir):
        # we store service manifests in a '.gilliam' directory in the
        # rootdir of the project
        return os.path.join(rootdir, '.gilliam', '%s.manifest' % (
                self.name,))

    def _make_manifest(self, path, approot):
        m = _read_or_create_manifest(path)
        m.update(approot)
        m.write(path)
        return m

    def _detect_missing(self, builder, m):
        hashes = [e['hash'] for (fn, e) in m.files.items()
                  if e.has_key('hash')]
        return builder.missing_files(hashes)
    
    def _upload_missing(self, builder, approot, m, files):
        for fn in files:
            e = m.files[fn]
            with open(os.path.join(approot, fn)) as fp:
                builder.put_file(e['hash'], fp)

    def _build_image(self, config, builder, m):
        repository = '%s/%s-%s' % (config.repository,
                                   config.formation,
                                   self.name)
        response = builder.build(m, repsitory, m.tag())
        for line in response.iter_lines():
            print line
