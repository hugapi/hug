Install the latest
===================

To install the latest version of hug simply run:

```bash
pip3 install hug --upgrade
```

Ideally, within a virtual environment.

Changelog
=========
### 2.3.1 - In progress
- Implemented improved way to retrieve list of urls and handlers for issue #462

### 2.3.0 - May 4, 2017
- Falcon requirement upgraded to 1.2.0
- Enables filtering documentation according to a `base_url`
- Fixed a vulnerability in the static file router that allows files in parent directory to be accessed
- Fixed issue #392: Enable posting self in JSON data structure
- Fixed issue #418: Ensure version passed is a number
- Fixed issue #399: Multiple ints not working correctly for CLI interface
- Fixed issue #461: Enable async startup methods running in parallel
- Fixed issue #412: None type return for file output format
- Fixed issue #464: Class based routing now inherit templated parameters
- Fixed issue #346: Enable using async routes within threaded server
- Implemented issue #437: Added support for anonymous APIs
- Added support for exporting timedeltas to JSON as seconds
- Added support for endpoint-specific input formatters:
```python
def my_input_formatter(data):
    return ('Results', hug.input_format.json(data))

@hug.get(inputs={'application/json': my_input_formatter})
def foo():
    pass
```
- Adds support for passing in a custom scheme in hug.test
- Adds str() and repr() support to hug_timer directive
- Added support for moduleless APIs
- Improved argparser usage message
- Implemented feature #427: Allow custom argument deserialization together with standard type annotation
- Improvements to exception handling.
- Added support for request / response in a single generator based middleware function
- Automatic reload support for development runner
- Added support for passing `params` dictionary and `query_string` arguments into hug.test.http command for more direct modification of test inputs
- Added support for manual specifying the scheme used in hug.test calls
- Improved output formats, enabling nested request / response dependent formatters
- Breaking Changes
    - Sub output formatters functions now need to accept response & request or **kwargs
    - Fixed issue #432: Improved ease of sub classing simple types - causes type extensions of types that dont take to __init__
                        arguments, to automatically return an instanciated type, beaking existing usage that had to instanciate
                        after the fact
    - Fixed issue #405: cli and http @hug.startup() differs, not executed for cli, this also means that startup handlers
      are given an instance of the API and not of the interface.

### 2.2.0 - Oct 16, 2016
- Defaults asyncio event loop to uvloop automatically if it is installed
- Added support for making endpoints `private` to enforce lack of automatic documentation creation for them.
- Added HTTP method named (get, post, etc) routers to the API router to be consistent with documentation
- Added smart handling of empty JSON content (issue #300)
- Added ability to have explicitly unversioned API endpoints using `versions=False`
- Added support for providing a different base URL when extending an API
- Added support for sinks when extending API
- Added support for object based CLI handlers
- Added support for excluding exceptions from being handled
- Added support for **kwarg handling within CLI interfaces
- Allows custom decorators to access parameters like request and response, without putting them in the original functions' parameter list
- Fixed not found handlers not being imported when extending an API
- Fixed API extending support of extra features like input_format
- Fixed issue with API directive not working with extension feature
- Fixed nested async calls so that they reuse the same loop
- Fixed TypeError being raised incorrectly when no content-type is specified (issue #330)
- Fixed issues with multi-part requests (issue #329)
- Fixed documentation output to exclude `api_version` and `body`
- Fixed an issue passing None where a text value was required (issue #341)

### 2.1.2 - May 18, 2016
- Fixed an issue with sharing exception handlers across multiple modules (Thanks @soloman1124)
- Fixed how single direction (response / request) middlewares are bounded to work when code is Cython compiled

### 2.1.1 - May 17, 2016
- Hot-fix release to ensure input formats don't die with unexpected parameters

### 2.1.0 - May 17, 2016
- Updated base Falcon requirement to the latest: 1.0.0
- Added native support for using asyncio methods (Thanks @rodcloutier!)
- Added improved support for `application/x-www-form-urlencoded` forms (thanks @cag!)
- Added initial support for `multipart/form-data`
- Added support for getting URL from hug function
- Added support for using `hug.local()` on methods in addition to functions
- Added a default mime-type for static file endpoints (`application/octet-stream`)
- Added initial `hug.API(__name__).context` dictionary as a safe place to store global per-thread state (such as database connections)
- Added support for manually specifying API object for all decorators (including middleware / startup) to enable easier plugin interaction
- Added support for selectively removing requirements per endpoint
- Added conditional output format based on Accept request header, as detailed in issue #277
- Added support for dynamically creating named modules from API names
- Improved how `hug.test` deals with non JSON content types
- Fixed issues with certain non-standard content-type values causing an exception
- Fixed a bug producing documentation when versioning is used, and there are no routes that apply accros versions
- Fixed a bug in the `hug_documentation` directive
- Breaking Changes
    - Input formats no longer get passed `encoding` but instead get passed `charset` along side all other set content type parameters

### 2.0.7 - Mar 25, 2016
- Added convenience `put_post` router to enable easier usage of the common `@hug.get('url/', ('PUT', 'POST"))` pattern
- When passing lists or tuples to the hug http testing methods, they will now correctly be handled as multiple values

### 2.0.5 - 2.0.6 - Mar 25, 2016
- Adds built-in support for token based authentication

### 2.0.4 - Mar 22, 2016
- Fixes documentation on PyPI website

### 2.0.3 - Mar 22, 2016
- Fixes hug.use module on Windows

### 2.0.2 - Mar 18, 2016
- Work-around bug that was keeping hug from working on Windows machines
- Introduced a delete method to the abstract hug store module

### 2.0.1 - Mar 18, 2016
- Add in-memory data / session store for testing
- Default hug.use.HTTP to communicate over JSON body

### 2.0.0 - Mar 17, 2016
- Adds the concept of chain-able routing decorators
- Adds built-in static file handling support via a `@hug.static` decorator (thanks @BrandonHoffman!)
- Adds a directive to enable directly accessing the user object from any API call (thanks @ianthetechie)
- Adds the concept of seamless micro-services via the hug.use module, enable switching between HTTP and local without code change
- Adds built-in support for 'X-Api-Key' header based authentication via `authentication.api_key`
- Adds support for running arbitrary python functions at runtime via a `@hug.startup` decorator
- Adds support for smarter handling of html output types
- Adds a UUID type
- Adds support for explicit API creation / referencing using `hug.api(__name__)`
- Adds a logging middleware to simplify the process of logging all requests with hug
- Adds a `middleware_class` class decorator, to enable quickly registering middleware classes
- Adds `smart_redirection` allowing API functions to return other endpoints
- Adds support for class based handlers
- Adds support for automatically handling exceptions
- Adds support for automatically outputting images with `save` method that don't take a format.
- Added extended support for delimited fields, enabling use of custom delimiters
- Added support for running different transformers based on content_type
- Added support for outputting a different response output type based on the response content_type
- Added support for running different transformations and outputting different content_types based on path suffix
- Added support for automatically supporting a set of suffixes at the end of a URL
- Added support for automatically adding headers based on route match
- Added support for quickly adding cache header based on route match
- Added support for quickly adding allow origin header based on route match
- Added support for quickly re-routing to defined 404 handler
- Added support for length based types (`length`, `shorter_than`, and `longer_than`)
- Added support for easily extending hugs JSON outputter with support for custom types
- Added support for a custom final pass validation function
- Added support for defining routes separate from handlers
- Added support for raising on validation errors - to enable overall exception handlers to catch them
- Added support for multiple transformers on an endpoint via `transform.all`
- Added support for applying type annotations and directives locally with @hug.local()
- Added support for a base_url by doing `hug.API(__name__).http.base_url = '/base_url'`
- Added support for automatically running CLI commands from hug command line runner
- Added requirements to documentation
- Updated all default output formats to gracefully handle error dictionaries
- Documentation generation was moved to API instances to enable easier customization
- Now correctly identifies and handles custom encodings
- Improved integration with Falcon so that primary elements (like status codes) can be imported directly from hug
- Added the ability to specify a transformer for validation errors per request handler, via `on_invalid` decorator argument
- Added the ability to specify an output format specific to validation errors per request handler, via `output_invalid` decorator argument
- Changed transform functions to get ran on output of validation errors by default
- Automatically works around a bug in uwsgi when returning byte streams
- Refactored how interfaces are built to be more reasuable, and more easily introspected
- Refactored how the built in annotation types are built to be more easily built upon
- Updated type.string to fail if a list is passed in
- Removed 'cli_behaviour' from types, instead moving the responsibility of per-type behavior to the CLI interface
- Fixed a bug that leaked annotation provided directives to the produced documentation
- Fully re-factored hug's type system for easier extensibility
- Breaking Changes
    - directives are no longer automatically applied to local function calls, '@hug.local' must be used to apply them
    - cli_behaviour has been removed as a type feature - however common sense inheritance of base types should easily replace it's usage
    - documentation module has been removed, in favor of documentation being generated by the api object and individual interfaces
    - API singleton now has sub-apis for each interface in use (IE hug.API(__name__).http and hug.API(__name__).cli)
    - run module has been removed, with the functionality moved to hug.API(__name__).http.server() and the terminal functionality
      being moved to hug.development_runner.hug

### 1.9.9 - Dec 15, 2015
- Hug's json serializer will now automatically convert decimal.Decimal objects during serializationkw
- Added `in_range`, `greater_than`, and `less_than` types to allow easily limiting values entered into an API

### 1.9.8 - Dec 1, 2015
- Hug's json serializer will now automatically convert returned (non-list) iterables into json lists

### 1.9.7 - Dec 1, 2015
- Fixed a bug (issue #115) that caused the command line argument for not auto generating documentation `-nd` to fail

### 1.9.6 - Nov 25, 2015
- Fixed a bug (issue #112) that caused non-versioned endpoints not to show up in auto-generated documentation, when versioned endpoints are present

### 1.9.5 - Nov 20, 2015
- Improved cli output, to output nothing if None is returned

### 1.9.3 - Nov 18, 2015
- Enabled `hug.types.multiple` to be exposed as nargs `*`
- Fixed a bug that caused a CLI argument when adding an argument starting with `help`
- Fixed a bug that caused CLI arguments that used `hug.types.multiple` to be parsed as nested lists

### 1.9.2 - Nov 18, 2015
- Improved boolean type behavior on CLIs

### 1.9.1 - Nov 14, 2015
- Fixes a bug that caused hug cli clients to occasionally incorrectly require additional arguments
- Added support for automatically converting non utf8 bytes to base64 during json output

### 1.9.0 - Nov 10, 2015
- Added initial built-in support for video output formats (Thanks @arpesenti!)
- Added built-in automatic support for range-requests when streaming files (such as videos)
- Output formatting functions are now called, even if a stream is returned.
- Input formatting functions now need to be responsible for dealing with text encoding and streaming
- Added additional default input format for `text/plain` and a few other common text based formats
- If no input format is available, but the body parameter is requested - the body stream is now returned
- Added support for a generic `file` output formatter that automatically determines the content type for the file

### 1.8.2 - Nov 9, 2015
- Drastically improved hug performance when dealing with a large number of requests in wsgi mode

### 1.8.1 - Nov 5, 2015
- Added `json` as a built in hug type to handle urlencoded json data in a request
- Added `multi` as a built in hug type that will allow a single field to be one of multiple types

### 1.8.0 - Nov 4, 2015
- Added a `middleware` module make it easier to bundle generally useful middlewares going forward
- Added a generic / reusable `SessionMiddleware` (Thanks @vortec!)

### 1.7.1 - Nov 4, 2015
- Fix a bug that caused error messages sourced from exceptions to be double quoted

### 1.7.0 - Nov 3, 2015
- Auto supply `response` and `request` to output transformations and formats when they are taken as arguments
- Improved the `smart_boolean` type even further, to allow 0, 1, t, f strings as input
- Enabled normal boolean type to easily work with cli apps, by having it interact via 'store_true'

### 1.6.5 - Nov 2, 2015
- Fixed a small spelling error on the `smart_boolean` type

### 1.6.2 - Nov 2, 2015
- Added a `mapping` type that allows users to quikly map string values to Python types
- Added a `smart_boolean` type that respects explicit true/false in string values

### 1.6.1 - Oct 30, 2015
- Added support for overriding parameters via decorator to ease use of **kwargs
- Added built-in boolean type support
- Improved testing environment

### 1.6.0 - Oct 13, 2015
- Adds support for attaching hug routes to method calls
- Hug is now compiled using Cython (when it is available) for an additional performance boost

### 1.5.1 - Oct 1, 2015
- Added built-in support for serializing sets

### 1.5.0 - Sep 30, 2015
- Added built-in support for outputting svg images
- Added support for rendering images from pygal graphs, or other image framworks that support `render`, automatically
- Added support for marshmallow powered output transformations
- Added support for marshmallow schema powered input types
- Added support for using individual marshmallow fields directly as input types
- Added support for attaching directives to specific named parameters, allowing directives to be used multiple times in a single API call
- Added support for attaching named directives using only the text name of the directive

### 1.4.0 - Sep 14, 2015
- Added *args support to hug.cli
- Added built-in html output support
- Added multi-api composition example to examples folder
- Fixed issue #70: error when composing two API modules into a single one without directives
- Fixed issue #73: README file is incorrectly formatted on PYPI

### 1.3.1 - Sep 8, 2015
- Fixed string only annotations causing exceptions when used in conjunction with `hug.cli`
- Fixed return of image file not correctly able to set stream len information / not correctly returning with PIL images
- Added examples of image loading with hug

### 1.3.0 - Sep 8, 2015
- Started keeping a log of all changes between releases
- Added support for quickly exposing functions as cli clients with `hug.cli` decorator
- Added support for quickly serving up development APIs from withing the module using: `if __name__ == '__main__': __hug__.serve()`
- Added support for documentation only type annotations, simply by passing just a string in as the type annotation
- Added support for `requires` argument to limit execution of functions based on a given criteria
- Added automatic documentation of output type transformations
- Added initial built-in authentication support
- Added built-in support for outputting common image file types
- Added support for returning streams within hugged functions
- `hug.types.decimal` renamed to `hug.types.float_number` and `hug.types.decimal` type added that returns python Decimal
- `hug.types.accept` wrapper added, that makes it easy to customize doc strings and error handling for any preexisting type converter
