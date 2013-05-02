This is the command-line client for Gilliam, a platform for 12 factor
applications.

# Installation

Note: As of now, it has only been tested on Ubuntu 12.04. 

It is recommended that you install in a virtual environment
(`virtualenv`) rather than risking your systems python installation:

    virtualenv .
    ./bin/pip install -r requirements.txt
    ./bin/python setup.py install

If you activate the virtual environment you should now be able to
execute the `gilliam` tool.

Set up your environment:

    export GILLIAM_SCHEDULER=http://localhost:8000/
    export GILLIAM_BUILDER=http://localhost:8001/

Substitute `localhost` for the hosts where you have the other
components running.

You're wise to make these environment variables persistent.

# Basic Commands

Here we go through the basic commands, all of which has not yet been
implemented.  Work in progress, as usual.

## Create an Application

This command creates a new application.  You give it a name (that must
be unique) and an optional description.

    $ gilliam create python-example

This does not build anything.  It just registers the application.


## Deploying

The `gilliam deploy` command deploys HEAD of your git repository to
the scheduler, via the build server. 

    $ gilliam deploy
    -----> Receiving app bundle...
    -----> Python app detected
    ...
    -----> App image size -> 28M
    -----> Deploying release ... v1 released
    

## Config

A release is the combination of software and configuration.  It is
not possible to change configuration without doing a new release.

The basics for altering the configuration:

    $ gilliam config [config params]

So for example, to deploy a release build two config parameters;
`POOL_SIZE=10` and `CONN_LIMIT=100`, issue the following command:

    $ gilliam config POOL_SIZE=10 CONN_LIMIT=100

If something is already deployed then those settings will be inherited
to the next invokation of `config`.  Say that you just wanna change
the `POOL_SIZE` setting to 16:

    $ gilliam config POOL_SIZE=16

This will result in a new release still with the same software version
and `CONN_LIMIT` set to 100, but now with a pool size of 16.


## Scaling

*scaling factors* are set on releaes to spawn processes of that
release.  Having the factors on releases rather than on the
application allows us to do partial rollout.  

The number of instances for process type is controlled using the
`scale` command:

    $ gilliam scale v1 web=4

You can display the current scaling factors by issuing `scale` without
any arguments:

    $ gilliam scale
    v1 web=4


## Showing Processes

When you have set your scaling factors the scheduler will start to
create process instances for you.  To get a list of these processes
you can run the `ps` command:

    $ gilliam ps
    web.EXwuYvDyXbASobnNwyRmNJ v1 state running (a minute ago) on host localhost port 10000

