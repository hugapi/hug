FROM python:alpine

ENV app=template

RUN pip install hug

ADD $app app

EXPOSE 8000

CMD hug -f /app/__init__.py

