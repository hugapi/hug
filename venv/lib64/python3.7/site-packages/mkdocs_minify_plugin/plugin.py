import os
import sys
import fnmatch
from timeit import default_timer as timer
from datetime import datetime, timedelta

from mkdocs import utils as mkdocs_utils
from mkdocs.config import config_options, Config
from mkdocs.plugins import BasePlugin
import mkdocs.structure.files

from jsmin import jsmin
from htmlmin import minify

class MinifyPlugin(BasePlugin):

    config_scheme = (
        ('minify_html', mkdocs.config.config_options.Type(bool, default=False)),
        ('minify_js', mkdocs.config.config_options.Type(bool, default=False)),
        ('js_files', mkdocs.config.config_options.Type((str, list), default=None))
    )

    def __init__(self):
        self.enabled = True
        self.total_time = 0

    def on_post_page(self, output_content, page, config):
        if self.config['minify_html']:
            return minify(output_content)
        else:
            return output_content

    def on_pre_build(self, config):
        if self.config['minify_js']:
            jsfiles = self.config['js_files'] or []
            if not isinstance(jsfiles, list):
                jsfiles = [jsfiles]                                        
            for jsfile in jsfiles:
                # Change extra_javascript entries so they point to the minified files
                if jsfile in config['extra_javascript']:
                    config['extra_javascript'][config['extra_javascript'].index(jsfile)] = jsfile.replace('.js', '.min.js')
        return config
    
    def on_post_build(self, config):
        if self.config['minify_js']:
            jsfiles = self.config['js_files'] or []
            if not isinstance(jsfiles, list):
                jsfiles = [jsfiles]                                        
            for jsfile in jsfiles:
                # Minify
                input_filename = config['site_dir'] + '/' + jsfile
                if os.sep != '/':
                    input_filename = input_filename.replace(os.sep, '/')
                output_filename = input_filename.replace('.js','.min.js')
                minified = ''
                # Read original file and minify
                with open(input_filename) as inputfile:
                    minified = jsmin(inputfile.read())
                # Write minified output file
                with open(output_filename, 'w') as outputfile:
                    outputfile.write(minified)
                # Delete original file
                os.remove(input_filename)
        return config
