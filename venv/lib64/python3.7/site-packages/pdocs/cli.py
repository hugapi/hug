import hug

from pdocs import api, logo

cli = hug.cli(api=hug.API(__name__, doc=logo.ascii_art))
cli(api.as_html)
cli(api.as_markdown)
cli(api.server)
