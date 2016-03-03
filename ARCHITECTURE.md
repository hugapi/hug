The guiding thought behind the architecture
===================
hug is the cleanest way to create HTTP REST APIs on Python3.
It consistently benchmarks among the top 3 performing web frameworks for Python, handily beating out Flask and Django.
For almost every common Web API task the code written to accomplish it in hug is a small fraction of what is required in other Frameworks.

However, it's important to note, hug is not a Web API Framework. OK -- that certainly is a function it performs. And exceptionally well at that.
But at its core, hug is a framework for exposing idiomatically correct and standard internal Python APIs externally.
A framework to allow developers and architects to define logic and structure once, and then cleanly expose it over other means.

Currently, this means that you can expose existing Python functions / APIs over HTTP and CLI in addition to standard Python.
However, as time goes on more interfaces will be supported. The architecture and implementation decisions that have going
into hug have and will continue to support this goal.

This central concept also frees hug to rely on the fastest and best of breed components for every interface it supports:

- Falcon is leveraged when exposing to HTTP for it's impressive performance at this task
- Argparse is leveraged when exposing to CLI for the clean consistent interaction it enables from the command line


What this looks like in practice - an illustrative example
===================
Let's say I have a very simple python API I've built to add 2 numbers together. I call my invention `addition`.
Trust me, this is legit. It's trademarked and everything:

    """A simple API to enable adding two numbers together"""


    def add(number_1, number_2):
        """Returns the result of adding number_1 to number_2"""
        return number_1 + number_2

It works, it's well documented, and it's clean.
Several people are already importing and using my Python module for their math needs.
However, there's a great injustice! I'm lazy, and I don't want to have to have open a Python interpreter etc to access my function.
Here's how I modify it to expose it via the command line:

    """A simple API to enable adding two numbers together"""
    import hug


    @hug.cli()
    def add(number_1, number_2):
        """Returns the result of adding number_1 to number_2"""
        return number_1 + number_2


    if __name__ == '__main__':
        add.interface.cli()

Yay! Now I can just do my math from the command line using `add.py $NUMBER_1 $NUMBER_2`.
And even better, if I miss an argument it let's me know what it is and how to fix my error.
The thing I immediately notice, is that my new command line interface works, it's well documented, and it's clean.
Just like the original.

However, users are not satisfied. I keep updating my API and they don't want to have to install a new copy every time.
They demand a Web API so they can always be pointing to my latest and greatest without restarting their apps and APIs.
No problem. I'll just expose it over HTTP as well:

    """A simple API to enable adding two numbers together"""
    import hug


    @hug.get() # <-- This is the only additional line
    @hug.cli()
    def add(number_1, number_2):
        """Returns the result of adding number_1 to number_2"""
        return number_1 + number_2


    if __name__ == '__main__':
        add.interface.cli()

That's it. I then run my new service via `hug -f add.py` and can see it running on `http://localhost:8000/`.
The default page shows me documentation that points me toward `http://localhost:8000/add?number_1=1&number_2=2` to perform my first addition.
The thing I immediately notice, is that my new web interface works, it's well documented, and it's clean.
Just like the original. Even better, after all of this, people hitting the API via Python didn't have to change anything.
All my original unit tests continue to pass and my code coverage remains at 100%.

It turns out, the problems and thoughts that go into defining a clean well documented API for internal use greatly mirror those that are required to expose an API for external use. hug recognizes this and enables cleanly reusing the documentation, requirements, and structure of internal APIs for external use. This also encourages easier to use and well documented internal APIs: a major win/win.

What happened internally as I exposed my API to new interfaces?
===================
A few things hapen when you wrapped that first function for external use, with hug.cli():

-   hug created a singleton hug.API object on your module to keep track of all interfaces that exist within the module
    - This is referable by `__hug__` or `hug.API(__name__)`
-   a new hug.interface.CLI() object was created and attached to `add.interface.cli`
    - This interface fully encapsulates the logic needed to expose `add` as a command line tool
    - NOTE: all supported ways to expose a function via hug can be found in `hug/interface.py`
-   the original Python `add` function is returned unmodified (with exception to the `.interface.cli` property addition)

Then when I extended my API to run as HTTP service the same basic pattern was followed:

-   hug saw that the singleton already existed
-   a new hug.interface.HTTP() object was created and attached to `add.interface.http`
    - This interface encapsulates the logic needed to expose the `add` command as an HTTP service
    - The new HTTP interface handler is registered to the API singleton
-   the original Python `add` function is returned unmodified (with exception to the `.interface.http` property addition)

At the end of this, I have 2 interface objects attached to my original function: `add.cli` and `add.http`.
Which is consistent with what I want to accomplish, one Python API with 2 additional external interfaces.

When I start the service via the command line, I call the `add.cli` interface directly which executes the code
producing a command line tool to interact with the add function.

When I run `hug -f add.py` the hug runner looks for the
`__hug__` singleton object and then looks for all registered HTTP interfaces, creating a Falcon WSGI API from them.
It then uses this new Falcon API to directly handle incoming HTTP requests.

Where does the code live for these core pieces?
===================
While hug has a lot of modules that enable it to provide a great depth of functionality, everything accomplished above,
and that is core to hug, lives in only a few:

-   `hug/api.py`: Defines the hug per-module singleton object that keeps track of all registered interfaces, alongside the associated per interface APIs (HTTPInterfaceAPI, CLIInterfaceAPI)
-   `hug/routing.py`: holds all the data and settings that should be passed to newly created interfaces, and creates the interfaces from that data.
    - This directly is what powers `hug.get`, `hug.cli, and all other function to interface routers
    - Can be seen as a Factory for creating new interfaces
-   `hug/interface.py`: Defines the actual interfaces that manage external interaction with your function (CLI and HTTP).

These 3 modules define the core functionality of hug, and any API that uses hug will inevitably utilize these modules.
Develop a good handling on just these and you'll be in great shape to contribute to hug, and think of new ways to improve the Framework.

Beyond these there is one additional internal utility library that enables hug to do it's magic: `hug/introspect.py`.
This module provides utility functions that enable hugs routers to determine what arguments a function takes and in what form.

Enabling interfaces to improve upon internal functions
===================
hug provides several mechanisms to enable your exposed interfaces to have additional capabilities not defined by
the base Python function.

- Enforced type annotations: hug interfaces automatically enforce type annotations you set on functions
    `def add(number_1:hug.types.number, number_2:hug.types.number):`
    - These types are simply called with the data passed into that field, if an exception is thrown it's seen as invalid
    - all of hugs custom types to be used for annotation are defined in `hug/types.py`
- Directives: hug interfaces allow replacing Python function parameters with dynamically pulled data via directives.
    `def add(number_1:hug.types.number, number_2:hug.types.number, hug_timer=2):`
    - In this example `hug_timer` is directive, when calling via a hug interface hug_timer is replaced with a timer that contains the starting time.
    - All of hug's built-in directives are defined in hug/directives.py
- Requires: hug requirements allow you to specify requirements that must be met only for specified interfaces.
    `@hug.get(requires=hug.authentication.basic(hug.authentication.verify('User1', 'mypassword')))`
    - Causes the HTTP method to only succesfully call the Python function if User1 is logged in
    - requirements are currently highly focused on authentication, and all existing require functions are defined in hug/authentication.py
- Transformations: hug transformations enable changing the result of a function but only for the specified interface
    `@hug.get(transform=str)`
    - The above would cause the method to return a stringed result, while the original Python function would still return an int.
    - All of hug's built in transformations are defined in `hug/transform.py`
- Input / Output formats: hug provides an extensive number of built-in input and output formats.
    `@hug.get(output_format=hug.output_format.json)`
    - These formats define how data should be sent to your API function and how it will be returned
    - All of hugs built-in output formats are found in `hug/output_format.py`
    - All of hugs built-in input formats are found in `hug/input_format.py`
    - The default assumption for output_formatting is JSON

Switching from using a hug API over one interface to another
===================
hug does it's best to also solve the other side of the coin: that is how APIs are used.
Naturally, native Python will always be the fastest, however HTTP can provide attractive auto updating
and clear responsibility separation benefits. You can interact with hug APIs via hug.use.[interface] if the ability
to switch between these is a high priority for you. The code that enables this is found in `hug/use.py` and should be
kept in mind if working on adding an additional interface for hug, or changing how hug calls functions.

Feel free to update or request more info :)
===================
I tried my best to highlight where important functionality in the hug project lives via this Architecture document, as well as
explain the reasoning behind it. However, this document is certainly not complete! If you encounter anything you would like to be
expanded upon or explained in detail here, please either let me know or modify the document so everyone can get a good walk through of hugs architecture.

Thanks!

I hope you have found this guide useful :)

~Timothy
