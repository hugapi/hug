# Docker/NGINX with Hug

Example of a Docker image containing a Python project utilizing NGINX, Gunicorn, and Hug. This example provides a stack that operates as follows:

```
Client <-> NGINX <-> Gunicorn <-> Python API (Hug)
```

## Getting started

Clone repository, navigate to directory where repository was cloned, then:

__For production:__
```
$ make prod
```

__For development:__
```
$ make dev
```

Once the docker images are running, navigate to `localhost:8000`. A `hello world` message should be visible!
