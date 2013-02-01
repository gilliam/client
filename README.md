# The Gilliam Client

Gilliam is a platform for deploying your [12 factor
apps](http://12factor.net/), and this is command-line client tool
allowing your to create and deploy apps.

# Installation

It has only been tested on Ubuntu 12.04.  It is recommended that you
install in a virtual environment (`virtualenv`) rather than risking
your systems python installation:

    $ git clone git@github.com:gilliam/client.git
    $ cd client
    $ virtualenv .
    $ ./bin/pip install -r requirements.txt
    $ ./bin/python setup.py install

If you activate the virtual environment you should now be able to
execute the `gilliam` tool.

Copy the example config file to your home directory:

    $ cp example.conf ~/.gilliam

# Config Files

There's a configuration file called `.gilliam` that lives in your home
directory.  This is a YAML file that defines where different
components of Gilliam can be located.  Check the `example.conf`
example file.

# Basic Commands

Here we go through the basic commands, all of which has not yet been
implemented.  Work in progress, as usual.

## Create an Application

This command creates a new "app" in the orchestrator.  You give it a
name (that must be unique) and then a URL where the code can be found.

    $ gilliam create python-example https://github.com/gilliam/python-example.git

This does not build anything.  It just registers the application and
the source URL for future use.

## Building an Image

Before you can do your first deploy you must build your application
code into something that can be deployed.  Simply issue the `build`
command to build your `master` branch from the repository you
specified when you created the app using the *create* command.

    $ gilliam build
    ...
    done: build is called '6dc2f9e'.
    

It is possible to specify a commit (tag, branch or hash) if you want
to build something special from the repository:

    $ gilliam build hot-fix-branch-2
    ...
    done: build is called 'hot-fix-branch-2'.

Each build receive a name. Use this name when you refer to your build
when you want to deploy it.

## Deploying

A deploy is the union of a build and configuration.  It is not
possible to change build without doing a new deploy and the same is
true for the configuration.

The basics of the deploy command is simple:

    $ gilliam deploy [build] [config params]

So for example, to deploy build called `6dc2f9e` with two config
parameters; `POOL_SIZE=10` and `CONN_LIMIT=100`, issue the following
command:

    $ gilliam deploy 6dc2f9e POOL_SIZE=10 CONN_LIMIT=100

If something is already deployed then those settings will be inherited
to the next invokation of `deploy`.  Say that you just wanna change
the `POOL_SIZE` setting to 16:

    $ gilliam deploy POOL_SIZE=16

This will result in a new deploy still with build `6dc2f9e` and
`CONN_LIMIT` set to 100, but now with a pool size of 16.

Issuing the command without any parameters will display some
information about the current deploy.  Use the `gilliam config`
command to display the active configuration.

## Setting Scale Values for an Application

The number of instances for an app process is controlled using the
`scale` command:

    $ gilliam scale web=4

Besides setting absolute values it is possible to give a delta to the
current scale.

    $ gilliam scale web=+1

(It is of course possible to give negative deltas.)
