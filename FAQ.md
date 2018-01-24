# Frequently Asked Questions about Hug

Q: I need to ensure the security of my data. Can Hug be used over HTTPS?

A: *Not directly, but you can utilize [uWSGI][https://uwsgi-docs.readthedocs.io/en/latest/] with nginx to transmit sensitive data. HTTPS is not part of the standard WSGI application layer, so you must use a WSGI HTTP server (such as uWSGI) to run in production. With this setup, Nginx handles SSL connections, and transfers requests to uWSGI.*

Q:  