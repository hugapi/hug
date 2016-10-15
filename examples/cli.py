"""A basic cli client written with hug"""
import hug

@hug.cli()
def cli(*values):
    return values

if __name__ == '__main__':
    cli.interface.cli()
