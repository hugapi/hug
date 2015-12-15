Changelog
=========

### 1.3.0
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

### 1.3.1
- Fixed string only annotations causing exceptions when used in conjunction with `hug.cli`
- Fixed return of image file not correctly able to set stream len information / not correctly returning with PIL images
- Added examples of image loading with hug

### 1.4.0
- Added *args support to hug.cli
- Added built-in html output support
- Added multi-api composition example to examples folder
- Fixed issue #70: error when composing two API modules into a single one without directives
- Fixed issue #73: README file is incorrectly formatted on PYPI

### 1.5.0
- Added built-in support for outputting svg images
- Added support for rendering images from pygal graphs, or other image framworks that support `render`, automatically
- Added support for marshmallow powered output transformations
- Added support for marshmallow schema powered input types
- Added support for using individual marshmallow fields directly as input types
- Added support for attaching directives to specific named parameters, allowing directives to be used multiple times in a single API call
- Added support for attaching named directives using only the text name of the directive

### 1.5.1
- Added built-in support for serializing sets

### 1.6.0
- Adds support for attaching hug routes to method calls
- Hug is now compiled using Cython (when it is available) for an additional performance boost

### 1.6.1
- Added support for overriding parameters via decorator to ease use of **kwargs
- Added built-in boolean type support
- Improved testing environment

### 1.6.2
- Added a `mapping` type that allows users to quikly map string values to Python types
- Added a `smart_boolean` type that respects explicit true/false in string values

### 1.6.5
- Fixed a small spelling error on the `smart_boolean` type

### 1.7.0
- Auto supply `response` and `request` to output transformations and formats when they are taken as arguments
- Improved the `smart_boolean` type even further, to allow 0, 1, t, f strings as input
- Enabled normal boolean type to easily work with cli apps, by having it interact via 'store_true'

### 1.7.1
- Fix a bug that caused error messages sourced from exceptions to be double quoted

### 1.8.0
- Added a `middleware` module make it easier to bundle generally useful middlewares going forward
- Added a generic / reusable `SessionMiddleware` (Thanks @vortec!)

### 1.8.1
- Added `json` as a built in hug type to handle urlencoded json data in a request
- Added `multi` as a built in hug type that will allow a single field to be one of multiple types

### 1.8.2
- Drastically improved hug performance when dealing with a large number of requests in wsgi mode

### 1.9.0
- Added initial built-in support for video output formats (Thanks @arpesenti!)
- Added built-in automatic support for range-requests when streaming files (such as videos)
- Output formatting functions are now called, even if a stream is returned.
- Input formatting functions now need to be responsible for dealing with text encoding and streaming
- Added additional default input format for `text/plain` and a few other common text based formats
- If no input format is available, but the body parameter is requested - the body stream is now returned
- Added support for a generic `file` output formatter that automatically determines the content type for the file

### 1.9.1
- Fixes a bug that caused hug cli clients to occasionally incorrectly require additional arguments
- Added support for automatically converting non utf8 bytes to base64 during json output

### 1.9.2
- Improved boolean type behavior on CLIs

### 1.9.3
- Enabled `hug.types.multiple` to be exposed as nargs `*`
- Fixed a bug that caused a CLI argument when adding an argument starting with `help`
- Fixed a bug that caused CLI arguments that used `hug.types.multiple` to be parsed as nested lists

### 1.9.5
- Improved cli output, to output nothing if None is returned

### 1.9.6
- Fixed a bug (issue #112) that caused non-versioned endpoints not to show up in auto-generated documentation, when versioned endpoints are present

### 1.9.7
- Fixed a bug (issue #115) that caused the command line argument for not auto generating documentation `-nd` to fail

### 1.9.8
- Hug's json serializer will now automatically convert returned (non-list) iterables into json lists

### 1.9.9
- Hug's json serializer will now automatically convert decimal.Decimal objects during serialization
- Added a `in_range` type to allow easily limiting numbers to specific ranges
