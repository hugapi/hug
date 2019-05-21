"""A basic cli client written with hug"""
import hug


@hug.CLIRouter(version="1.0.0")
def cli(name: "The name", age: hug.types.number):
    """Says happy birthday to a user"""
    return "Happy {age} Birthday {name}!\n".format(**locals())


if __name__ == "__main__":
    cli.interface.cli()
