# Frequently Asked Questions about Hug

For more examples, check out Hug's [documentation][https://github.com/timothycrosley/hug/tree/develop/documentation] and [examples][https://github.com/timothycrosley/hug/tree/develop/examples] Github directories, and its [website][http://www.hug.rest/].

## General Questions

Q: *Can I use Hug with a web framework -- Django for example?*

A: You can use Hug alongside Django or the web framework of your choice, but it does have drawbacks. You would need to run hug on a separate, hug-exclusive server. You can also [mount Hug as a WSGI app][https://pythonhosted.org/django-wsgi/embedded-apps.html], embedded within your normal Django app. 




## Technical Questions

Q: *I need to ensure the security of my data. Can Hug be used over HTTPS?*

A: Not directly, but you can utilize [uWSGI][https://uwsgi-docs.readthedocs.io/en/latest/] with nginx to transmit sensitive data. HTTPS is not part of the standard WSGI application layer, so you must use a WSGI HTTP server (such as uWSGI) to run in production. With this setup, Nginx handles SSL connections, and transfers requests to uWSGI.

Q:  *How can I serve static files from a directory using Hug?*

A: For a static HTML page, you can just set the proper output format as: `output=hug.output_format.html`. To see other examples, check out the [html_serve][https://github.com/timothycrosley/hug/blob/develop/examples/html_serve.py] example, the [image_serve][https://github.com/timothycrosley/hug/blob/develop/examples/image_serve.py] example, and the more general [static_serve][https://github.com/timothycrosley/hug/blob/develop/examples/static_serve.py] example within `hug/examples`.

Most basic examples will use a format that looks something like this: 

```Python

@hug.static('/static')
￼def my_static_dirs():
￼    return('/home/www/path-to-static-dir')
```

Q: *Does Hug support autoreloading?*

A: Hug supports any WSGI server that uses autoreloading, for example Gunicorn and uWSGI. The scripts for initializing autoreload for them are, respectively:

Gunicorn: `gunicorn --reload app:__hug_wsgi__`
uWSGI: `--py-autoreload 1 --http :8000 -w app:__hug_wsgi__`

Q: *How can I access a list of my routes?*

A: You can access a list of your routes by using the routes object on the HTTP API:

`__hug_wsgi__.http.routes`

It will return to you a structure of "base_url -> url -> HTTP method -> Version -> Python Handler". Therefore, for example, if you have no base_url set and you want to see the list of all URLS, you could run: 

`__hug_wsgi__.http.routes[''].keys()`

Q: *How can I configure a unique 404 route?*

A: By default, Hug will call `documentation_404()` if no HTTP route is found. However, if you want to configure other options (such as routing to a directiory, or routing everything else to a landing page) you can use the `@hug.sink('/')` decorator to create a "catch-all" route:

```Python 

import hug

@hug.sink('/all')
def my_sink(request):
    return request.path.replace('/all', '')
```





