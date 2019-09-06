"""This module defines CLI interaction when using `portray`.

This is powered by [hug](https://github.com/hugapi/hug) which means unless necessary
it should maintain 1:1 compatibility with the programmatic API definition in the
[API module](/reference/portray/api)

- `portray as_html`: Renders the project as HTML into the `site` or other specified output directory
- `portray in_browser`: Runs a server with the rendered documentation pointing a browser to it
- `portray server`: Starts a local development server (by default at localhost:8000)
- `portray project_configuration`: Returns back the project configuration as determined by` portray`
"""
from pprint import pprint

import hug

from portray import api, logo

cli = hug.cli(api=hug.API(__name__, doc=logo.ascii_art))
cli(api.as_html)
cli.output(pprint)(api.project_configuration)
cli(api.server)
cli(api.in_browser)
cli(api.on_github_pages)
