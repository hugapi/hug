import hug

output_format = hug.output_format.json
input_format = {'application/json': hug.input_format.json}
directives = {'timer': hug.directives.Timer, 'api': hug.directives.api, 'module': hug.directives.module,
              'current_api': hug.directives.CurrentAPI}
