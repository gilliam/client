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

"""\
Client tool for Gilliam.

Usage: gilliam [options] <command> [<args>...]

Options:
    -h, --help  Display this help text and exit.
    --version   Show version and quit.
    --app <APP> Specify specific app.

Commands:
    create      Create a new application
    ps          Display processes of app
    config      Show current configuration
    scale       Set scale for a release

See `gilliam help <command>` for more information on a specific
command.
"""

from docopt import docopt
import json
import os.path
import requests
import subprocess
import yaml
from fnmatch import fnmatch
import sys
from textwrap import dedent
import yaml
import os
from urlparse import urljoin
import dateutil.parser


from xgilliam.util import from_now, format_timedelta, urlchild, pretty_date
from xgilliam.api import SchedulerAPI, BuilderAPI


COMMANDS = {}


def expose(name):
    """Expose a function as a command."""
    def decl(f):
        COMMANDS[name] = f
        return f
    return decl


class Config(object):
    """Wraps our configuration files.

    There are two files.  One YAML file called `.gilliam` living in
    the home directory.  This file contains pointers to the
    orchestrator and the build server.  The second file `.gilliam.app`
    is just a simple text file with the name of the current app.
    """

    CONF = '.gilliam'
    ATTACH = '.gilliam.app'

    def __init__(self):
        self._config = None
        self._attach = None

    def _read_config(self):
        for path in (self.CONF, os.path.expanduser('~/' + self.CONF)):
            if os.path.exists(path):
                with open(path) as fp:
                    self._config = yaml.load(fp)
                break
        else:
            raise RuntimeError("No config file")
    
    def _read_attach(self):
        if self._attach is None:
            if not os.path.exists(self.ATTACH):
                raise RuntimeError("Not attached to an app")
            with open(self.ATTACH) as fp:
                self._attach = fp.read().strip()
        return self._attach

    @property
    def app(self):
        return self._read_attach()

    def set_app(self, app):
        self._attach = app

    def scheduler(self):
        return SchedulerAPI(self, requests)

    def builder(self):
        return BuilderAPI(self._builder_url(), requests)

    def set_app(self, name):
        """Set C{name} as active app."""
        with open(self.ATTACH, 'wb') as fp:
            fp.write(name)
        self._attach = name

    def _builder_url(self):
        return os.getenv("GILLIAM_BUILDER")

    @property
    def app_url(self):
        """Return base URL to the attached app in the orchestrator."""
        attach = self._read_attach()
        return urlchild(self.orch_url, 'app', attach)
        
    @property
    def orch_url(self):
        """Return base URL to the orchestrator."""
        self._read_config()
        return 'http://%s:%d' % (self._config['orchestrator']['host'],
                                  self._config['orchestrator']['port'])


@expose("create")
def create(config, app_options, argv):
    """\
    Usage: gilliam create <NAME> [DESCRIPTION]

    Create a new app called NAME with code living at REPOSITORY.
    """
    options = docopt(create.__doc__, argv=argv)
    current = orch_api.create_app(options['<NAME>'],
        options['DESCRIPTION'] or options['<NAME>'],)
    config.set_app(options['<NAME>'])


@expose("releases")
def releases(config, app_options, argv):
    """\
    Show releases of the app.

    Usage: gilliam releases
    """
    options = docopt(releases.__doc__, argv=argv)

    for release in config.scheduler().releases():
        dt = dateutil.parser.parse(release['timestamp'])
        print "v%-6d %-20s %s" % (release['version'],
                                  pretty_date(dt),
                                  release['text'])


@expose("release")
def do_release(config, app_options, argv):
    """\
    Release.

    Usage: gilliam release [options] <IMAGE> 

    Options:
        -m, --message MESSAGE  Message describing release
        -b, --build BUILD      Which build
        -P, --procfile PATH    Read process types from here.
    """
    options = docopt(do_release.__doc__, argv=argv)

    scheduler = config.scheduler()
    release = scheduler.release()

    if not options['--procfile']:
        sys.exit("Must specify path to Procfile.")
    with open(options['--procfile']) as fp:
        pstable = yaml.load(fp)

    release = scheduler.create_release(
        options.get('--message', 'none'),
        options.get('--build', 'unknown'),
        options['<IMAGE>'],
        pstable,
        release['config'] if release else {})
    print "v%d released" % (release['version'],)


def read_in_chunks(infile, chunk_size=1024*64):
    c = 0
    while True:
        chunk = infile.read(chunk_size)
        c += len(chunk)
        if chunk:
            yield chunk
        else:
            break
    print "READ", c


@expose("deploy")
def deploy(config, app_options, argv, stdout=sys.stdout):
    """\
    Deploy a new software version.

    Usage: gilliam deploy [options]

    Options:
        -m, --message MESSAGE  Message describing release
        -b, --build BUILD      Which build    
    """
    options = docopt(deploy.__doc__, argv=argv)
    if not options['--build']:
        options['--build'] = subprocess.check_output(
            ["git", "describe", "--always", "--tags"]).strip()
    if not options['--message']:
        options['--message'] = 'Deploy %s' % (options['--build'],)
    request = {'app': config.app, 'commit': options['--build'],
               'text': options['--message']}
    # stream data from "git archive" straigth into the request.
    process = subprocess.Popen(["git", "archive", "--format=tar", "HEAD"],
                               stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT)
    for output in config.builder().deploy(process.stdout, config.app,
                                          options['--build'],
                                          options['--message']):
        stdout.write(output)


@expose("ps")
def ps(config, app_options, argv):
    """\
    Show procs and their status.

    Usage: gilliam ps
    """
    options = docopt(ps.__doc__, argv=argv)
    scheduler = config.scheduler()

    for proc in scheduler.procs():
        print "%s v%d state %s (%s) on host %s port %s" % (
            proc['name'], proc['release']['version'], proc['state'],
            pretty_date(dateutil.parser.parse(proc['changed_at'])),
            proc['host'], str(proc['port']) if proc['port'] else 'none')


@expose("scale")
def scale(config, app_options, argv):
    """\
    Set scale parameters for a release.

    Usage: gilliam scale [<VERSION> [<SPEC>...]]
    """
    def _format_scale(scale):
        return ' '.join([('%s=%d' % (pt, n)) for pt, n in scale.items()])

    options = docopt(scale.__doc__, argv=argv)
    scheduler = config.scheduler()
    if options['<VERSION>']:
        if not options['<VERSION>'].startswith("v"):
            sys.exit("%s: invalid version" % (argv[0],))
        version = options['<VERSION>'][1:]
        release = scheduler.release(version)
        current = release['scale'].copy()
        if options['<SPEC>']:
            for spec in options['<SPEC>']:
                proc, value = spec.split('=', 1)
                if proc not in release['pstable']:
                    sys.exit("%s: %s: no such proc according to deploy" % (
                            argv[0], proc))
                if value[0] in ('+', '-'):
                    current[proc] = max(0, current.get(proc, 0) + int(value))
                else:
                    current[proc] = int(value)
            scheduler.set_scale(version, current)
    else:
        for release in scheduler.releases():
            if release['scale']:
                print "v%d %s" % (release['version'],
                                  _format_scale(release['scale']))


@expose("config")
def display_config(config, app_options, argv):
    """\
    Change or display configuration.

    Usage: gilliam config [CONFIG...]
    """
    options = docopt(display_config.__doc__, argv=argv)
    scheduler = config.scheduler()
    release = scheduler.release()
    if release is None:
        sys.exit("No release.")
    if options['CONFIG']:
        app_config = release['config'].copy()
        for pair in options['CONFIG']:
            name, value = pair.split('=', 1)
            app_config[name] = value
        release = scheduler.create_release('Config change', 
                                           release['build'],
                                           release['image'],
                                           release['pstable'],
                                           app_config)
        print "v%d released" % (release['version'],)
    else:
        for k, v in release['config'].items():
            print "%s=%r" % (k, v) 


@expose("restart")
def restart(config, app_options, argv):
    """\
    Restart a specific proc.

    Usage: gilliam restart NAME
    """
    options = docopt(restart.__doc__, argv=argv)
    config.scheduler().restart_proc(options['NAME'])


@expose("help")
def help(config, app_options, argv, stdout=sys.stdout):
    """\
    Display help for a command.

    Usage: gilliam help [COMMAND]
    """
    options = docopt(help.__doc__, argv=argv)
    if not options['COMMAND']:
        stdout.write(dedent(__doc__))
    elif not options['COMMAND'] in COMMANDS:
        sys.exit("gilliam: help: %s: no such command" % (
                options['COMMAND'],))
    else:
        command = COMMANDS[options['COMMAND']]
        stdout.write(dedent(command.__doc__))


def main():
    options = docopt(__doc__, version='gilliam 0.0', options_first=True)
    command = options.get('<command>', 'help')
    if command not in COMMANDS:
        sys.exit("Unknown command")
    config = Config()
    if options['--app']:
        config.set_app(options['--app'])
    try:
        COMMANDS[command](config, options, [command] + options['<args>'])
    except RuntimeError, re:
        sys.exit(str(re))
