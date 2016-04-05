hug output formats
===================

Every endpoint that is exposed through an externally facing interface will need to return data in a standard, easily understandable format.

The default output format for all hug APIs is JSON. However, you may explicitly specify a different default output_format:

    hug.API(__name__).output_format = hug.output_format.html

or:

    @hug.default_output_format()
    def my_output_formatter(data, request, response):
        # Custom output formatting code

Or, to specify an output_format for a specific endpoint, simply specify the output format within its router:

    @hug.get(output=hug.output_format.html)
    def my_endpoint():
        return # HTML generating code goes here

You can use route chaining to specify an output format for a group of endpoints within an API:

    html = hug.get(output=hug.output_format.html)

    @html
    def my_endpoint_1():
        return # HTML generating code goes here

    @html.urls('/')
    def root():
        return # HTML generating code goes here

Finally, an output format may be a collection of different output formats that get used conditionally. For example, using the built-in suffix output format:

    suffix_output = hug.output_format.suffix({'.js': hug.output_format.json,
                                              '.html':hug.output_format.html})

    @hug.get(('my_endpoint.js', 'my_endoint.html'), output=suffix_output)
    def my_endpoint():
        return ''

In this case, if the endpoint is accesed via my_endpoint.js, the output type will be JSON; however if it's accesed via my_endoint.html, the output type will be HTML.

Built-in hug output formats
===================

hug provides a large catalog of built-in output formats, which can be used to build useful APIs right away:

 - `hug.output_format.json`: The default hug output formatter for all endpoints; outputs in Javascript Serialized Object Notation (JSON).
 - `hug.output_format.text`: Outputs in a plain text format.
 - `hug.output_format.html`: Outputs Hyper Text Markup Language (HTML).
 - `hug.output_format.json_camelcase`: Outputs in the JSON format, but first converts all keys to camelCase to better conform to Javascript coding standards.
 - `hug.output_format.pretty_json`: Outputs in the JSON format, with extra whitespace to improve human readability.
 - `hug.output_format.image(format)`: Outputs an image (of the specified format).
    - There are convience calls in the form `hug.output_format.{FORMAT}_image for the following image types: 'png', 'jpg', 'bmp', 'eps', 'gif', 'im', 'jpeg', 'msp', 'pcx', 'ppm', 'spider', 'tiff', 'webp', 'xbm',
               'cur', 'dcx', 'fli', 'flc', 'gbr', 'gd', 'ico', 'icns', 'imt', 'iptc', 'naa', 'mcidas', 'mpo', 'pcd',
               'psd', 'sgi', 'tga', 'wal', 'xpm', and 'svg'.
    Automatically works on returned file names, streams, or objects that produce an image on read, save, or render.

 - `hug.output_format.video(video_type, video_mime, doc)`: Streams a video back to the user in the specified format.
    - There are convience calls in the form `hug.output_format.{FORMAT}_video for the following video types: 'flv', 'mp4', 'm3u8', 'ts', '3gp', 'mov', 'avi', and 'wmv'.
    Automatically works on returned file names, streams, or objects that produce a video on read, save, or render.

 - `hug.output_format.file`: Will dynamically determine and stream a file based on its content. Automatically works on returned file names and streams.

 - `hug.output_format.on_content_type(handlers={content_type: output_format}, default=None)`: Dynamically changes the output format based on the request content type.
 - `hug.output_format.suffix(handlers={suffix: output_format}, default=None)`: Dynamically changes the output format based on a suffix at the end of the requested path.
 - `hug.output_format.prefix(handlers={suffix: output_format}, defualt=None)`: Dynamically changes the output format based on a prefix at the begining of the requested path.

Creating a custom output format
===================

An output format is simply a function with a content type attached that takes a data argument, and optionally a request and response, and returns properly encoded and formatted data:

    @hug.format.content_type('file/text')
    def format_as_text(data, request=None, response=None):
        return str(content).encode('utf8')

A common pattern is to only apply the output format. Validation errors aren't passed in, since it's hard to deal with this for several formats (such as images), and it may make more sense to simply return the error as JSON. hug makes this pattern simple, as well, with the `hug.output_format.on_valid` decorator:

    @hug.output_format.on_valid('file/text')
    def format_as_text_when_valid(data, request=None, response=None):
        return str(content).encode('utf8')


