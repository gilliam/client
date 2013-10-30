# The Gilliam Command-Line Interface

Gilliam is a software platform for building and running distributed
systems.

This is the command-line tool that is used to control services running
on the Gilliam platform.


## Installation

Install using pip (preferably in a virtualenv) straight from the
repository:

    $ pip install git+https://github.com/gilliam/client.git

That's it. The command is called `gilliam-cli`.

# Quick Intro

First a few words about Gilliam application model: A *service* is a
piece of code that runs on the platform.  It can be some business
logic, a cache or a database.  Services are grouped together into a
*formation*.  Code and configuration in the form of environment
variables are merged together into a *release*.  *Instances* of a
service can be created from a release.  Everything live in a *stage*,
which is another word for a gilliam installation.

In this quick into we'll use a small python example to showcase some
of the commands of the client.  First, we need to clone the example
code:

    $ git clone git+https://github.com/gilliam/python-example.git
    $ cd python-example

Lets take a look at the `gilliam.yml` file:

    www:
      script: python web.py
      ports: [80]

A `gilliam.yml` file specifies a set of services that the formation
need to expose functionality.  In file above contains just a single
service `www`.  The `script` tells us that when the service is started
the command `python web.py` should be executed.  `ports` specifies
ports on which the service can receive incoming requests.

Gilliam comes with a whole set of different service types. The type
for a service can always be specified with a `type` field.  But you
can also let it to Gilliam to figure out the type; the type will then
be deduced from the service name and its definition.

Back to the example.

To create a formation for the example issue the following command:
    
    $ gilliam-cli --stage myapp-prod create example

We specify `--stage myapp-prod` to tell the client to create the
formation in the `myapp-prod` stage (the production environment for my
application).

*Note*: This quick into does not take into consideration how the stage
is created.

Next step is to build and deploy:

    $ gilliam-cli deploy
    start building service 'www' ...
     |        Python app detected
     | -----> No runtime.txt provided; assuming python-2.7.4.
    ...
     |        Successfully installed Flask Werkzeug Jinja2 markupsafe
     |        Cleaning up...
     |        Cleaning up caches
    released 1

When done, a new release has been created. You can see it if you do a
`gilliam-cli releases`:

    $ gilliam-cli releases        
    name      author          message
    --------- --------------- ----------------------------------------
    1         jrydberg        None

Gilliam allows heterogeneous set ups where you have instances from
multiple releases running at the same time.  This allows you to build
sophisticated build pipelines with canary tests.

But right now, nothing is running, since we have not scaled the
release.  So lets do that:

    $ gilliam-cli scale 1 www=1
    $

This will create an instance of the `www` service and dispatch it to
one of the executors. Run `gilliam-cli ps` to inspect instances:

    $ gilliam-cli ps
    name                                release state
    ----------------------------------- ------- ---------
    www.BHCrBMebfG4oZUgix95chH          1       running

...

# Basic Commands

## Creating a Formation

## Building a Release

## Scaling a Release

(FIXME: default to last release, or to <all releases> somehow?)

## Migrating to a Release

## Deploying (Build + Migrate)

