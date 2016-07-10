FROM python:alpine
MAINTAINER Housni Yakoob <housni.yakoob@gmail.com>

EXPOSE 8000

RUN pip3 install gunicorn
RUN pip3 install hug -U
WORKDIR /src
CMD gunicorn --reload --bind=0.0.0.0:8000 __init__:__hug_wsgi__