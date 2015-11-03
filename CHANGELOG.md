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

### 1.6.7
- Improved the `smart_boolean` type even further, to allow 0, 1, t, f strings as input
- Enabled normal boolean type to easily work with cli apps, by having it interact via 'store_true'
