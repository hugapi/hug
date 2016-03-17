hug directives (automatic argument injection)
===================

Often times you'll find yourself needing something particular to an interface (say a header, a session, or content_type) but don't want to tie your function
to a single interface. To support this: hug introduces the concept of `directives`. In hug directives are simply arguments that have been registered to automatically provide a parameter value based on knowledge known to the interface.

For example - this is the built in session directive:


    @hug.directive()
    def session(context_name='session', request=None, **kwargs):
        """Returns the session associated with the current request"""
        return request and request.context.get(context_name, None) or None

Then when using this directive in your code, you can either specify the directive via type annotation:

    @hug.get()
    def my_endpoint(session: hug.directives.session):
        session # is here automatically, without needing to be passed in

Or, prefixing the argument with `hug_`:

    @hug.get()
    def my_endpoint(hug_session):
        session # is here automatically, without needing to be passed in

You can then specify a different location for the hug session, simply by providing a default for the argument:

    @hug.get()
    def my_endpoint(hug_session='alternative_session_key'):
        session # is here automatically, without needing to be passed in

Built-in directives
===================

hug provides a handful of directives for commonly needed attributes:

 - hug.directives.Timer (hug_timer=precision): Stores the time the interface was initially called, returns how much time has passed since the function was called if casted as a float. Automatically converts to a the time taken when returned as part of a JSON structure. The default value is used to specify the float precision desired when keeping track of the time passed
 - hug.directives.module (hug_module): Passes along the module that contains the API associated with this endpoint
 - hug.directives.api (hug_api): Passes along the hug API singleton associated with this endpoint
 - hug.directives.api_version (hug_api_version): Passes along the version of the API being called
 - hug.directives.documentation (hug_documentation): Generates and passes along the entire set of documentation for the API the endpoint is contained within
 - hug.directives.session (hug_session=context_name): Passes along the session associated with the current request. The default value is used to provide a different key where the value is stored on the request.context object.
 - hug.directives.user (hug_user): Passes along the user object associated with the request
 - hug.directives.CurrentAPI (hug_current_api): Passes along a smart version aware API caller, to enable calling other functions within your API with reissurence the correct function is being called for the version of the API being requested

Building custom directives
===================

hug provides the `@hug.directive()` to enable creation of new directives. It takes one argument: apply_globally which defaults to False.
If you set this parameter to True the hug directive will be automatically made available as a magic `hug_` argument on all endpoints outside of just your defined API. This is not a concern if your applying directives via type annotation.

The most basic directive will simply take an optional default value, and **kwargs:

    @hug.directive()
    def basic(default=False, **kwargs):
        return str(default) + ' there!'


This directive could then be used like this:

    @hug.local()
    def endpoint(hug_basic='hi'):
        return hug_basic

    assert endpoint() == 'hi there!'

It's important to always accept **kwargs for directive functions as each interface get's to decide it's own set of
key word arguments to send to the directive, which can then be used to pull-in information for the directive.

Common directive key word parameters
===================

Independ of what interface a directive is being ran through, the following key word arguments will be passed to it:

 - `interface` - the interface that the directive is being ran through. Useful for conditionally injecting different data via the decorator depending on the interface it is being called through:

    @directive()
    def my_directive(default=None, interface=None, **kwargs):
        if interface == hug.interface.CLI:
            return 'CLI specific'
        elif interface == hug.interface.HTTP:
            return 'HTTP specific'
        elif interface == hug.interface.Local:
            return 'Local'

        return 'unknown'
 - `api` - the API singleton associated with this endpoint

HTTP directive key word parameters
===================

Directives are passed the following additional keyword parameters when they are being ran through an HTTP interface:

 - `response`: The HTTP response object that will be returned for this request
 - `request`: The HTTP request object that caused this interface to be called
 - `api_version`: The version of the endpoint being hit

CLI directive key word parameters
===================

Directives get one additional argument when they are being ran through a command line interface:

 - `argparse`: The argparse instance created to parse command line arguments
