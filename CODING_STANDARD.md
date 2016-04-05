Coding Standard
=========
Any submission to this project should closely follow the [PEP 8](https://www.python.org/dev/peps/pep-0008/) coding guidelines with the exceptions:

1. Lines can be up to 120 characters long.
2. Single letter or otherwise nondescript variable names are prohibited.

Standards for new hug modules
=========
New modules added to the hug project should all live directly within the `hug/` directory without nesting.
If the modules are meant only for internal use within hug they should be prefixed with a leading underscore. For example, `def _internal_function`.
Modules should contain a doc string at the top that gives a general explanation of the purpose and then
restates the project's use of the MIT license.

There should be a `tests/test_$MODULE_NAME.py` file created to correspond to every new module that contains
test coverage for the module. Ideally, tests should be 1:1 (one test object per code object, one test method
per code method) to the extent cleanly possible.
