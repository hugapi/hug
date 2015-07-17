# HUG
Everyone needs a hug. Even API developers. Hug aims to make developing Python driven APIs as simple as possible, but no simpler.
This one is for you :).
=====

[![PyPI version](https://badge.fury.io/py/hug.png)](http://badge.fury.io/py/hug)
[![PyPi downloads](https://pypip.in/d/hug/badge.png)](https://crate.io/packages/hug/)
[![Build Status](https://travis-ci.org/timothycrosley/hug.png?branch=master)](https://travis-ci.org/timothycrosley/hug)
[![License](https://img.shields.io/github/license/mashape/apistatus.svg)](https://pypi.python.org/pypi/hug/)

Hug drastically simplifies Python API development. With hug you can focus on how to write the best implementations,
and n

Hug's Design Objectives:

- Make developing a Python driven API as succint as a written definition.
- The framework should encourage code that self-documents.
- It should be fast. Never should a developer feel the need to look somewhere else for performance reasons.
- Writing tests for APIs written on-top of Hug should be easy and intuitive.
- Should be well document
- Magic done once, in an API, is better then pushing the problem set to the user of the API.

Write:

```python
import underscore as _

def my_function(argument1, argument2):
    if argument1:
        del argument2
    elif argument2:
        print(argument2)

    if somevar is someothervar And x is not b: pass
```


Get:

```javascript
var _ = require('_');

function my_function(argument1, argument2) {
    if (argument1) {
        delete argument2;
    } else if (argument2) {
        console.log(argument2);
    }
    if (somevar === someothervar && x !== b) {}
}
```

in a hug.


Why hug?
======================

hug (pronounced: jiffy) simply stands for JavaScript In, Python Out.

Jiphy is very different from other attempts at Python -> JavaScript conversion for the following reasons:
 -  Converts in both directions (JavaScript -> Python, Python -> JavaScript).
 -  Allows intermixing of code. You can add a Python function to a JavaScript file and then convert it all to JavaScript.
 -  Converts lines 1:1, so you always know which source line causes which output line. No source mapping needed.
 -  Doesn't require any extra JavaScript files to be loaded.
 -  Can be used by a single developer without team buy-in.

Jiphy only supports syntax, but with ES6 around the corner should one day support Classes, default arguments, etc.


Important things to know when writing Python for conversion to JavaScript
===================

- Every indented block must have a line after it.

For instance:

    if something is True:
        do_something()

    print("done")

Is valid as the if statement has a new line after it. However:

    if something is True:
        do_something()
    print("done")

is NOT valid in Jiphy. The lack of a new line makes it impossible to do a 1:1 conversion and still be nicely formatted JS code.

- Jiphy isn't smart enough to know when to create a var

For now, you still have to write var in front of new variables in Jiphy. Jiphy simply does not yet have the smarts to know when it is and when it is not required.

- Jiphy does not implement stdlib components, classes, etc. It's SYNTAX ONLY.


Syntax / Contstructs Jiphy Suppports
===================
| Python                      | JavaScript        | Supported To JavaScript | Supported To Python |
|:----------------------------|:------------------|:-----------------------:|:-------------------:|
| def (...):                  | function(...) {}  |  ✓                      |  ✓                  |
| if ...:                     | if (...) {}       |  ✓                      |  ✓                  |
| while ...:                  | while (...) {}    |  ✓                      |  ✓                  |
| elif ...:                   | } else if (...) { |  ✓                      |  ✓                  |
| else:                       | } else {          |  ✓                      |  ✓                  |
| pass                        | {}                |  ✓                      |  ✓                  |
| print(...)                  | console.log(...)  |  ✓                      |  ✓                  |
| True                        | true              |  ✓                      |  ✓                  |
| False                       | false             |  ✓                      |  ✓                  |
| None                        | null              |  ✓                      |  ✓                  |
| Or                          | &#124;&#124;                | ✓                        |  ✓                  |
| And                         | &&                |  ✓                      |  ✓                  |
| Unset                       | undefined         |  ✓                      |  ✓                  |
| not                         | !                 |  ✓                      |  ✓                  |
| is                          | ===               |  ✓                      |  ✓                  |
| del                         | delete            |  ✓                      |  ✓                  |
| \n                          | ;\n               |  ✓                      |  ✓                  |
| # comment                   | // comment        |  ✓                      |  ✓                  |
| str(...)                    | String(...)       |  ✓                      |  ✓                  |
| bool(...)                   | Boolean(...)      |  ✓                      |  ✓                  |
| int(...)                    | Number(...)       |  ✓                      |  ✓                  |
| import pdb; pdb.set_trace() | debugger;         |  ✓                      |  ✓                  |
| try:                        | try {             |  ✓                      |  ✓                  |
| except                      | catch             |  ✓                      |  ✓                  |
| except Exception as e       | catch(e)          |  ✓                      |  ✓                  |
| .append(...)                | .push(...)        |  ✓                      |  ✓                  |
| raise 'error'               | throw 'error';    |  ✓                      |  ✓                  |
| import x                    | var x = require(x)|  ✓                      |                     |
| import x as _               | var _ = require(x)|  ✓                      |                     |
| "String"                    | 'String'          |  ✓                      |                     |
| """String"""                | 'Str' + 'ing'     |  ✓                      |                     |
| @decorator                  | f = decorator(f)  |  ✓                      |                     |


Installing hug
===================

Installing hug is as simple as:

    pip install hug

or if you prefer

    easy_install hug


Using hug
===================
**from the command line**:

    hug mypythonfile.py mypythonfile2.py

 or to conform all code to the specified file format

    hug mypythonfile.js mypythonfile2.js --conform

or recursively:

    hug -rc .

 *which is equivalent to*

    hug **/*.py

or recursively conform:

    hug -rc --conform .

or to see the proposed changes without applying them

    hug mypythonfile.py --diff

**from within Python**:

    import hug

    hug.to.javascript(python_code)
    hug.to.python(javascript_code)

--------------------------------------------

Thanks and I hope you find hug useful!

~Timothy Crosley
