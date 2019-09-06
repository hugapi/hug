SERVER_PORT = 8080
SERVER_HOST = "127.0.0.1"

HTML_OUTPUT_DIRECTORY = "site"
MARKDOWN_OUTPUT_DIRECTORY = "docs"

MARKDOWN_EXTENSIONS = [
    "markdown.extensions.abbr",
    "markdown.extensions.admonition",
    "markdown.extensions.attr_list",
    "markdown.extensions.def_list",
    "markdown.extensions.fenced_code",
    "markdown.extensions.footnotes",
    "markdown.extensions.tables",
    "markdown.extensions.smarty",
    "markdown.extensions.toc",
]
MARKDOWN_EXTENSION_CONFIGS = {
    "markdown.extensions.smarty": {
        "smart_angled_quotes": False,
        "smart_dashes": True,
        "smart_quotes": False,
        "smart_ellipses": True,
    }
}
