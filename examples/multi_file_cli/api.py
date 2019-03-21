import hug

import sub_api


@hug.cli()
def echo(text: hug.types.text):
    return text


@hug.extend_api(sub_command='sub_api')
def extend_with():
    return (sub_api, )


if __name__ == '__main__':
    hug.API(__name__).cli()
