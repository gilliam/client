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

"""
Usage: gilliam [--version] <command> [<args>...]

Commands:
    build       Issue a new build
    deploy      Deploy a new build or configuration
    config      Show current configuration
    status      Display current status for application
    create      Create a new application.
    attach      Attach environment to existing application

See `gilliam help <command>` for more information on a specific command.

"""

import sys
from docopt import docopt
import os.path
import yaml
import requests
import json


def urlchild(base_url, *args):
    return base_url + ''.join([('/%s' % arg) for arg in args])


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

    @property
    def builder_url(self):
        self._read_config()
        return 'http://%s:%d' % (self._config['builder']['host'],
                                  self._config['builder']['port'])


class BuilderAPI(object):
    """Abstraction that provides us with an API for building app
    images.
    """

    def __init__(self, config, requests):
        self.config = config
        self.requests = requests

    def _get_json(self, *parts):
        try:
            response = self.requests.get(urlchild(*parts))
            response.raise_for_status()
        except:
            raise
        else:
            return response.json()

    def create_build(self, app, repository, commit, stdout):
        """Create a new build with the given parameters."""
        request = {'repository': repository}
        if commit is not None:
            request['commit'] = commit
        response = self.requests.post(urlchild(self.config.builder_url,
            'build', app), data=json.dumps(request), stream=True)
        for data in response.iter_content():
            stdout.write(data)
        return self._get_json(response.headers['location'])


class API(object):
    """Abstraction that provides functions to talk to the orchestrator
    using its REST API.
    """

    def __init__(self, config, requests):
        self.config = config
        self.requests = requests

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

    def app(self):
        """Return the current app."""
        return self._get_json(self.config.app_url)

    def scale(self):
        """Return current scale values."""
        return self._get_json(self.config.app_url, 'scale')

    def set_scale(self, scale):
        """Set scale values."""
        self._put_json(scale, self.config.app_url, 'scale')

    def deploy(self):
        """Return current deploy as a C{dict}."""
        return self._get_json(self.config.app_url, 'deploy', 'latest')

    def create_deploy(self, build, image, pstable, app_config, text):
        """Create a new deploy."""
        try:
            request = {'build': build, 'image': image,
                       'pstable': pstable, 'config': app_config,
                       'text': text}
            response = self.requests.post(urlchild(
                self.config.app_url, 'deploy'),
                data=json.dumps(request))
            response.raise_for_status()
        except:
            raise
        else:
            return response.json()


@expose("attach")
def attach(config, app_options, argv, requests=requests):
    """Usage: gilliam attach APP

    Attach to a given app.
    """
    options = docopt(attach.__doc__, argv=argv)
    app_url = urljoin(config.orch_url, '/app/%s' % (options['APP'],))
    try:
        response = requests.get(app_url)
    except RequestException:
        raise
    else:
        if response.status == 400:
            sys.exit("%s: %s: no such app" % (argv[0], options['APP']))
        else:
            sys.exit("%s: server response: %r" % (argv[0], response))
        output = response.json()
        config.attach(options['APP'])


@expose("build")
def build(config, orch_api, builder_api, app_options, argv,
          stdout=sys.stdout):
    """Usage: gilliam build [--repository REPOSITORY] [COMMIT]
    """
    options = docopt(build.__doc__, argv=argv)
    if not options['--repository']:
        app = orch_api.app()
        options['--repository'] = app['repository']

    current = builder_api.create_build(config.app, options['--repository'],
        options['COMMIT'], stdout)

    print "done: build is called '%s'." % (current['name'],)


@expose("scale")
def scale(config, orch_api, builder_api, app_options, argv):
    """Usage: gilliam scale [<SPEC>...]

    Set scale parameters for procs.

    The SPEC is specified as a proc name and scale value, like
    `web=20`.  It is possible to increase or decrease the scale value
    using a `+` or `-` prefix.  For example `web=+2` will increase the
    scale for the web proc with two instances.
    """
    options = docopt(scale.__doc__, argv=argv)
    deploy = orch_api.deploy()
    current = orch_api.scale()
    if options['<SPEC>']:
        for spec in options['<SPEC>']:
            proc, value = spec.split('=', 1)
            if proc not in deploy['pstable']:
                sys.exit("%s: %s: no such proc according to deploy" % (
                        argv[0], proc))
            if value[0] in ('+', '-'):
                current[proc] = max(0, current.get(proc, 0) + int(value))
            else:
                current[proc] = int(value)
        orch_api.set_scale(current)
    for proc, value in current.items():
        print "%s=%d" % (proc, value)


@expose("config")
def display_config(config, orch_api, builder_api, app_options, argv):
    """Usage: gillaim config

    Display current deployed config.
    """
    options = docopt(display_config.__doc__, argv=argv)
    current = orch_api.deploy()
    for k, v in current['config'].items():
        print "%s=%r" % (k, str(v))


@expose("deploy")
def deploy(config, orch_api, builder_api, app_options, argv):
    """Usage: gilliam deploy [options] [BUILD] [CONFIG...]

    Options:
        -m, --message <message>   Deploy message

    """
    options = docopt(deploy.__doc__, argv=argv)
    argv = filter(None, [options['BUILD']] + options['CONFIG'])
    current = orch_api.deploy()
    if not argv:
        print "deploy %d: %s at %s: %s" % (current['id'],
            current['build'], current['when'], current['text'])
        return
    elif not '=' in argv[0]:
        options['BUILD'], argv = argv[0], argv[1:]
    else:
        options['BUILD'] = None
    build = options['BUILD'] or current['build']
    # update config with new settings if needed:
    app_config = current['config']
    for pair in argv:
        name, value = pair.split('=', 1)
        app_config[name] = value
    # FIXME: at this point we know the build and the config.  talk to
    # the buildserver to get hold of a URL to the image and the
    # pstable.
    pstable = {'web': 'pythob web.py'}
    image = 'app.tar.gz'
    message = options['--message'] or ('build %s%s' % (
            build, (' with config changes' if len(argv) else '')))
    orch_api.create_deploy(build, image, pstable, app_config, message)


@expose("help")
def help(app_options, argv):
    """."""
    # FIXME: todo.
    print "Help", args


def main():
    options = docopt(__doc__, version='gilliam 0.0', options_first=True)
    command = options.get('<command>', 'help')
    if command not in COMMANDS:
        sys.exit("Unknown command")
    config = Config()
    orch_api = API(config, requests)
    builder_api = BuilderAPI(config, requests)
    try:
        COMMANDS[command](config, orch_api, builder_api, options,
                          [command] + options['<args>'])
    except RuntimeError, re:
        sys.exit(str(re))
