#!/usr/bin/env python3
import tornado.ioloop
import tornado.web
import json


class TextHandler(tornado.web.RequestHandler):
    def get(self):
        self.write('Hello, world!')


application = tornado.web.Application([
    (r"/text", TextHandler),
])

if __name__ == "__main__":
    application.listen(8000)
    tornado.ioloop.IOLoop.current().start()
