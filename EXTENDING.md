Building hug extensions
=========
Want to extend hug to tackle new problems? Integrate a new form of authentication? Add new useful types?
Awesome! Here are some guidlines to help you get going and make a world class hug extension
that you will be proud to have showcased to all hug users.

How are extensions built?
=========
hug extensions should be built like any other python project and uploaded to PYPI. What makes a hug extension a *hug* extension is simply it's name and the fact it contains within its Python code utilities and classes that extend hugs capabilties.

Naming your extension
=========
All hug extensions should be prefixed with `hug_` for easy disscovery on PYPI. Additionally, there are a few more exact prefixes that can be optionally be added to help steer users to what your extensions accomplishes:

- `hug_types_` should be used if your extensions is used primarily to add new types to hug (for example: hug_types_numpy).
- `hug_authentication_` if your extension is used primarily to add a new authentication type to hug (for example: hug_authentication_oath2)
- `hug_output_format_` if your extension is used primarily to add a new output format to hug (for example: hug_output_format_svg)
- `hug_input_format_` if your extension is used primarily to add a new input format to hug (for example: hug_input_format_html)
- `hug_validate_` if your extension is used primarily to add a new overall validator to hug (for example: hug_validate_no_null).
- `hug_transform_` if your extension is used primarily to add a new hug transformer (for example: hug_transform_add_time)
- `hug_middleware_` if your extension is used primarily to add a middleware to hug (for example: hug_middleware_redis_session)

For any more complex or general use case that doesn't fit into these predefined categories or combines many of them, it
is perfectly suitable to simply prefix your extension with `hug_`. For example: hug_geo could combine hug types, hug input formats, and hug output formats making it a good use case for a simply prefixed extension.

Building Recommendations
=========
Ideally, hug extensions should be built in the same manner as hug itself. This means 100% test coverage using pytest, decent performance, pep8 compliance, and built in optional compiling with Cython. None of this is strictly required, but will help give users of your extension faith that it wont slow things down or break their setup unexpectedly.

Registering your extension
=========
Once you have finished developing and testing your extension, you can help increase others ability to discover it by registering it. The first place an extension should be registered is on PYPI, just like any other Python Package. In addition to that you can add your extension to the list of extensions on hug's github wiki: https://github.com/timothycrosley/hug/wiki/Hug-Extensions

Thank you
=========
A sincere thanks to anyone that takes the time to develop and register an extension for hug. You are helping to make hug a more complete eco-system for everyuser out there, and paving the way for a solid foundation into the future.

Thanks!

~Timothy Crosley
