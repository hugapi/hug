import hug


@hug.get()
@hug.cli()
def made_up_go():
    return 'Going!'
