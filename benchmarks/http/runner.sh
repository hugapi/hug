#!/bin/bash

output="Test results:\n"

for app in hug_test falcon_test flask_test bobo_test cherrypy_test pyramid_test  bottle_test;
do
    echo "TEST: $app"
    killall gunicorn
    fuser -k 8000/tcp
    gunicorn -w 2 $app:app &
    sleep 5
    ab -n 1000 -c 5 http://localhost:8000/text
    sleep 5
    ab_out=`ab -n 20000 -c 5 http://localhost:8000/text`
    killall gunicorn
    rps=`echo "$ab_out" | grep "Requests per second"`
    crs=`echo "$ab_out" | grep "Complete requests"`
    output="$output\n$app:\n\t$rps\n\t$crs"
done

echo -e "$output"


