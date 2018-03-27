# Docker/NGINX with Hug

Example of a Docker image containing a Python project utilizing NGINX, Gunicorn, and Hug. This example provides a stack that operates as follows:

```
Client <-> NGINX <-> Gunicorn <-> Python API (Hug)
```

## Getting started

Clone/copy this directory to your local machine, navigate to said directory, then:

__For production:__
This is an "immutable" build that will require restarting of the container for changes to reflect.
```
$ make prod
```

__For development:__
This is a "mutable" build, which enables us to make changes to our Python project, and changes will reflect in real time!
```
$ make dev
```

Once the docker images are running, navigate to `localhost:8000`. A `hello world` message should be visible!
