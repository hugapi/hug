"""A basic cli client written with hug"""
import hug


@hug.cli(version="1.0.0")
def cli(name, age:hug.types.number):
    """Says happy birthday to a user"""
    return "Happy {age} Birthday {name}!".format(**locals())


if __name__ == '__main__':
    cli.cli()
