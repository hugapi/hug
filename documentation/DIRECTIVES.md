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


