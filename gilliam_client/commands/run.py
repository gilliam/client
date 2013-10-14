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

from functools import partial
import contextlib
import fcntl
import random
import signal
import sys
import struct
import os
import termios
import yaml

from gilliam.util import thread


@contextlib.contextmanager
def console():
    fd = sys.stdin.fileno()
    isatty = os.isatty(fd)

    # make stdout unbuffered;
    sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)
    oldterm = termios.tcgetattr(fd)
    newattr = oldterm[:]
    newattr[3] = newattr[3] & ~termios.ICANON & ~termios.ECHO
    termios.tcsetattr(fd, termios.TCSANOW, newattr)

    try:
        yield 
    finally:
        if isatty:
            termios.tcsetattr(fd, termios.TCSAFLUSH, oldterm)

def istty():
    """Check if input to the program is a TTY."""
    return os.isatty(sys.stdin.fileno())


def terminal_size(fd):
    h, w, hp, wp = struct.unpack('HHHH',
        fcntl.ioctl(fd, termios.TIOCGWINSZ,
        struct.pack('HHHH', 0, 0, 0, 0)))
    return w, h


class Command(object):
    """\
    Run a command on an executor:

      gilliam-cli gilliam/base /bin/bash

    To get image from a service use `--service` and give the service
    name instead of image name.  The latest release will be used
    unless specified with `--release NAME`.

    Environment variables can be passed to the command with `--env':
    
      gilliam-cli run --env VAR=VALUE --env VAR2 ...

    If no value is specified for a variable it will be retrieved from
    the current environment.

    Give `--tty` to force a TTY to be opened for the command (will
    normally only be done if a TTY is connected to the current
    terminal).
    """

    synopsis = 'Run a command'

    def __init__(self, parser):
        parser.add_argument('--executor')
        parser.add_argument('-s', '--service', action="store_true",
                            help="get image from service")
        parser.add_argument('-r', '--release', metavar="NAME",
                            help="name of release",)
        parser.add_argument('-e', '--env', metavar="VAR", action='append')
        parser.add_argument('-t', '--tty', dest='tty', action='store_true',
                            help="force tty input even if ")
        parser.add_argument('image')
        parser.add_argument('command', nargs='*')

    def _release(self, config, options):
        try:
            name = int(options.release)
        except ValueError:
            with open(options.release) as fp:
                return yaml.load(fp)
        else:
            if not config.formation:
                sys.exit("require formation")
            scheduler = config.scheduler()
            releases = list(scheduler.releases(config.formation))
            releases.sort(key=lambda release: int(release['name']))
            for release in releases:
                if release['name'] == options.release:
                    return release
            return releases[-1] if releases else None

    def _make_env(self, options):
        env = {}
        for var in options.env:
            if '=' in var:
                var, value = var.split('=', 1)
            else:
                value = os.getenv(var)
                if value is None:
                    sys.exit("env variable %s not set" % (var,))
            env[var] = value
        return env

    def _service(self, config, options, env):
        release = self._release(config, options)
        service = release['services'].get(options.image)
        if service is None:
            sys.exit("no such service in release %s" % (release['name'],))

        options.image = service['image']
        if not options.command:
            options.command = service['command']
        env.update(service.get('env', {}))

    def _winch(self, process, *args):
        w, h = terminal_size(sys.stdin.fileno())
        process.resize_tty(w, h)

    def _select_executor(self, config, options):
        alts = config.service_registry.query_formation('executor')
        if options.executor:
            for alt in alts:
                if alt['instance'] == options.executor:
                    return alt
            sys.exit("cannot find executor instance %s" % (options.executor,))
        else:
            return random.choice([d for (k, d) in alts])

    def handle(self, config, options):
        instance = self._select_executor(config, options)
        executor = config.executor('%s.api.executor.service' % (
                instance['instance'],))
        env = {}

        tty = istty() or options.tty
        reader = (iter(partial(sys.stdin.read, 1), '') if tty else
                  iter(partial(sys.stdin.read, 4096), ''))

        if options.service:
            self._service(config, options, env)

        if options.env:
            env.update(self._make_env(options))

        command = None if not options.command else options.command

        process = executor.run(config.formation, options.image,
                               env, command, tty=tty)
        process.wait_for_state('running')

        if istty():
            with console():
                old_handler = signal.signal(signal.SIGWINCH, partial(
                        self._winch, process))
                thread(process.attach, reader, sys.stdout, replay=True)
                thread(self._winch, process)
                exit_code = process.wait()
            signal.signal(signal.SIGWINCH, old_handler)
        else:
            thread(process.attach, reader, sys.stdout)
            exit_code = process.wait()

        sys.exit(exit_code)
