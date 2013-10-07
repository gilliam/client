
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

"""There are two levels of configuration for the client: 

- the *global* configuration which includes data about stages (ie a
  running Gilliam installation) and cached credentials for
  authentication.

- the *formation* configuration that holds data and information that
  is related to the current formation and its project.  This
  configuration lives in `.gilliam` in the project directory.

Configuration is stored as plain text files.  If the file contains
some kind of structured data it is stored using YAML.  If the file
only contains a single value, it is stored just as a text string.

"""

from collections import namedtuple
import getpass
from functools import partial
import os.path
import os
import string
import yaml
import sys
import time
import errno

from gilliam.service_registry import ServiceRegistryClient
from gilliam.service_registry import Resolver
from gilliam.adapter import ResolveAdapter, WebSocketAdapter
from gilliam import (BuilderClient, ExecutorClient,
                     SchedulerClient, RouterClient)
from requests.adapters import HTTPAdapter
import requests


class FormationConfig(object):
    """Configuration that is related to the current formation. Lives
    in the project directory, called `rootdir` (normally alongside the
    `.git` directory).

    Configuration data is stored in plain text files in the `.gilliam`
    directory.
    """

    def __init__(self, rootdir):
        self.rootdir = rootdir

    def _read_file(self, name):
        try:
            with open(os.path.join(self.rootdir, '.gilliam', name)) as fp:
                return fp.read().strip()
        except EnvironmentError as err:
            if err.errno != errno.ENOENT:
                raise
            return None

    def _ensure_dir(self):
        try:
            os.makedirs(os.path.join(self.rootdir, '.gilliam'))
        except EnvironmentError as err:
            if err.errno != errno.EEXIST:
                raise

    def _write_file(self, name, value):
        try:
            self._ensure_dir()
            with open(os.path.join(self.rootdir, '.gilliam', name), 'w') as fp:
                fp.write(value)
        except EnvironmentError as err:
            raise

    @classmethod
    def make(cls, rootdir):
        return cls(rootdir)


for name in ['stage', 'formation']:
    def _property(name=name):
        def getter(self):
            return self._read_file(name)
        def setter(self, value):
            self._write_file(name, value)
        return getter, setter
    setattr(FormationConfig, name, property(*_property()))


_RAISE_ERROR = object()


class StageConfig(object):
    """Stage configuration holds information and data about
    installation of Gilliam, such as address to the service registry.
    The stage configuration is shared between all formations and
    normally live at `~/.gilliam/stage/<name>`.

    Most configuration variables can be overridden with environment
    variables.  For exammple, to override the `repository` config var,
    set the `GILLIAM_REPOSITORY` variable to the new value.
    """

    __vars__ = (
        ('repository', getpass.getuser(), str),
        ('service_registry', None, partial(string.split, sep=',')),
        )

    def __init__(self, path):
        self._path = path
        self._config = {}

    def set(self, var, value):
        """Set variable `var` to `value`.  If there already is a value
        for `var` in the configuration, it will be overwritten.
        """
        self._config[var] = value

    def get(self, var, default=_RAISE_ERROR):
        """Get variable `var`.  Return `default` if the there's no
        value for the variable in the configuration.  If `default` is
        not specified, the error `KeyError` will be raised.

        :param var: Name of configuration variable.

        :param default: (Optional) Default value that should be
            returned if the variable is not present in the
            configuration.

        :raises: KeyError
        :returns: The value of the variable or `default`.
        """
        val = self._config.get(var, default)
        if val is _RAISE_ERROR:
            raise KeyError("var %s not found in stage config" % (
                    var,))
        return val

    def items(self):
        """Get all configuration variables as a sequence of variable
        and value tuples.
        """
        return self._config.items()

    def _read(self):
        """Read config.

        :raises: IOError, OSError
        """
        with open(self._path) as fp:
            self._config.update(yaml.load(fp))

    def write(self, path=None):
        """Persist configuration.  `ValueError` will be raised if no
        path was given when object was created, to given to this
        method.
        
        :param path: (Optional) Path to where the data should be
            written.  If not specified, the path given when the object
            was created will be used.

        :raises: IOError, OSError, ValueError
        """
        path = path if path else self._path
        if path is None:
            raise ValueError("path not specified")
        with open(self._path, 'w') as fp:
            yaml.safe_dump(self._config, fp, encoding='utf-8', tags=None,
                           default_flow_style=False)

    def _override_from_environment(self):
        """Override configuration variables with values from the
        environment.
        """
        for (name, default, fmt) in self.__vars__:
            val = os.getenv('GILLIAM_' + name.upper())
            if val is not None:
                self.set(name, fmt(val))

    def _set_defaults(self):
        """Try to gather sane defaults."""
        for (name, default, fmt) in self.__vars__:
            if default is not None:
                self._config.setdefault(name, default)

    def check(self):
        """Check if the configuration contains enough information to
        be considered *valid*. If not, raise hell by raising
        `SystemExit` (via `sys.exit`).

        :raises: `SystemExit` if the configuration do not check out.
        """
        if not 'service_registry' in self._config:
            sys.exit("cannot find address to service registry")

    @classmethod
    def make(cls, path):
        """Construct a stage configuration by reading it from the
        given path.  Read values will be overriden by values from the
        environment, if present.

        The configuration will be checked before it is returned, so
        this function can raise the same errors as `check`.

        :returns: The stage config object.
        """
        c = cls(path)
        c._set_defaults()
        c._read()
        c._override_from_environment()
        c.check()
        return c

    @classmethod
    def default(cls):
        """Construct a stage configuration with only default values
        and data from the environment.

        The configuration will be checked before it is returned, so
        this function can raise the same errors as `check`.

        :returns: The stage config object.
        """
        c = cls(None)
        c._set_defaults()
        c._override_from_environment()
        c.check()
        return c


for (name, default, fmt) in StageConfig.__vars__:
    def _property(name=name):
        def getter(self):
            return self._config.get(name)
        def setter(self, value):
            self._config[name] = value
        return getter, setter
    setattr(StageConfig, name, property(*_property()))


Credentials = namedtuple('Credentials', ['username', 'password'])


class AuthConfig(object):
    """The auth config caches credentials for talking to different
    image registries, such as `index.docker.io`.  It's normally
    stored in `~/.gilliam/auth`.

    The cache can credentials for multiple registries at the same
    time.  The data is stored as a YAML file::

       index.registry.io:
         username: foo
         password: bar
    
    .. warning::
         
       Passwords are stored in **plain text**.  To increase the
       security level a bit, file permissions `0600` is set on the
       file.

    Create an object by calling `make`, giving it a path to the
    file.  This will read content of the file, if present::

       >>> ac = AuthConfig('.gilliam/auth')

    The `store` method is used to put credentials in the
    configuration::

       >>> ac.store('index.registry.io', 'my-user', 'my-pass')

    Note that to actually write the data to disk, the `write` method
    needs to be invoked.  The object also acts as a context manager::

       >>> ac.write()

    .. code-block:: python

       with ac:
         ac.store('index.registry.io', 'my-user', 'my-pass')
           
    To get credentials out of the registry, call `get` with the
    registry as argument.  You will get back a `Credentials` object
    that has two properties: `username` and `password`.  If there was
    no record for the registry, it returns `None`::

       >>> ac.get('index.registry.io')
       ...
       >>> ac.get('my-index.com')
       >>>
 
    """

    def __init__(self, path, credentials=None):
        self.path = path
        if credentials is None:
            credentials = {}
        self.credentials = credentials

    def get(self, registry):
        """Get credentials for `registry` or `None` if the config do
        not hold a entry for the registry.

        :returns: Credentials or `None`.
        """
        return self.credentials.get(registry)

    def store(self, registry, username, password):
        """Store credentials (username and password) for the given
        registry.  If there's already credentials for the registry,
        they will be overwritten.
        """
        self.credentials[registry] = Credentials(username=username,
                                                 password=password)

    def _read(self):
        """Read credentials from the file. Will replace existing
        credentials with the one read from the file.  If the file was
        empty, or not there, all credentials will be cleared.
        """
        try:
            with open(self.path, 'r') as fp:
                data = yaml.load(fp)
        except EnvironmentError as err:
            if err.errno != errno.ENOENT:
                raise
            data = {}

        self.credentials = {registry: Credentials(**cred)
                            for registry, cred in data.items()}

    def write(self):
        """Permanently store the credentials on disk.  After the file
        has been written, permission `0600` will be set.
        """
        try:
            os.makedirs(os.path.dirname(self.path))
        except OSError:
            pass

        data = {registry: {'username': cred.username,
                           'password': cred.password}
                for registry, cred in self.credentials.items()}

        with open(self.path, 'w') as fp:
            yaml.safe_dump(data, fp, default_flow_style=False)
        os.chmod(self.path, 0600)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.write()

    @classmethod
    def make(cls, path):
        """Read credentials from `path` and store them in a newly
        created `AuthConfig` object that is returned.  If the file
        does not exist, a empty object is returned.

        :params path: Path to where existing credentials are stored.
        :returns: Newly created `AuthConfig` object.
        """
        ac = cls(path)
        ac._read()
        return ac


class Config(object):
    """The configuration (aka the God object).  Holds all
    configuration more or less, including references to the stage,
    formation and auth configurations.

    The object also have factory methods for most service-related
    interfaces::

       >>> config = Config()
       >>> router = config.router()
       >>> router.routes()
       ...
    
    """

    def __init__(self, project_dir, stage_config, form_config, auth_config,
                 stage, formation):
        self.project_dir = project_dir
        self.stage_config = stage_config
        self.form_config = form_config
        self.auth_config = auth_config
        self.stage = stage
        self.formation = formation

        self.httpclient = requests.Session()
        self.service_registry = ServiceRegistryClient(time, stage_config.service_registry)
        self._resolver = Resolver(self.service_registry)
        self.httpclient.mount('http://', ResolveAdapter(HTTPAdapter(),
                                                        self._resolver))
        self.httpclient.mount('ws://', ResolveAdapter(WebSocketAdapter(),
                                                      self._resolver))

        self.scheduler = partial(SchedulerClient, self.httpclient)
        self.executor = partial(ExecutorClient, self.httpclient)
        self.builder = partial(BuilderClient, self.httpclient)
        self.router = partial(RouterClient, self.httpclient)

    @classmethod
    def make(cls, project_dir, stage_config, form_config, auth_config,
             stage, formation):
        return cls(
            project_dir, stage_config, form_config, auth_config, stage, formation
            )
