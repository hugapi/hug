# Framework Benchmarks

**UPDATE** - Further research has helped me figure out how to run 
more of the tests in Gunicorn. Given that, I've decided to use 
two workers instead of just one for these tests. 

**UPDATE 2** - These benchmarks helped the author of Hug find a bug. 
As of version 1.8.2 it's *way* faster. 

The benchmarks perform the following framework-specific tasks.

1. Route '/json' to a method.
2. Encode the '/json' result as JSON.
3. Return JSON in the response body with "Content-Type: application/json". 

## Requirements

1. The app MUST work under Python3.

## Running the tests

You'll need to install all specified frameworks. Python 3 was used.

    pip3 install bobo bottle cherrypy hug falcon flask pycnic pyramid gunicorn

Then:

    $ cd /path/to/pycnic/benchmarks
    $ ./runner.sh

## Methods

All WSGI frameworks are hosted with Gunicorn (single worker). 

    gunicorn -w 2 <framework>_test:app

The actual testing is performed with `ab`. 

    ab -n 5000 -c 5 http://localhost:8000/json

### Exceptions

* **tornado** was hosted using the built-in IOLoop.
* **muffin** was hosted with `muffin muffin_test run` due to various errors attempting to get it working with Gunicorn.
* **morepath** was disqualified for numerous errors and complexity issues. Interestingly enough, it installs through pip but does not uninstall.

## Results

[Chart](http://pycnic.nullism.com/images/pycnic-bench.png)

Output from `runner.sh` (for tests working with WSGI):

*Note: Falcon is running with Cython enabled, which provides a slight advantage*


    Test results:

    bobo_test:
        Requests per second:    2879.91 [#/sec] (mean)
        Complete requests:      5000
    falcon_test:
    	Requests per second:    3354.99 [#/sec] (mean)
    	Complete requests:      5000
    pycnic_test:
    	Requests per second:    3183.22 [#/sec] (mean)
    	Complete requests:      5000
    cherrypy_test:
        Requests per second:    1696.93 [#/sec] (mean)
        Complete requests:      5000
    pyramid_test:
    	Requests per second:    2785.36 [#/sec] (mean)
    	Complete requests:      5000
    flask_test:
    	Requests per second:    2372.21 [#/sec] (mean)
    	Complete requests:      5000
    bottle_test:
    	Requests per second:    3084.96 [#/sec] (mean)
    	Complete requests:      5000
    hug_test (1.8.2):
    	Requests per second:    3146.27 [#/sec] (mean)
    	Complete requests:      5000


Manually running tests for the others:

* **tornado** - 1341.86/sec, 3.762s
* **muffin** - 1080.41/sec, 4.628s


