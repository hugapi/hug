from pyramid.view import view_config
from pyramid.config import Configurator


@view_config(route_name='text', renderer='string')
def text(request):
    return 'Hello, World!'


config = Configurator()

config.add_route('text', '/text')

config.scan()
app = config.make_wsgi_app()
