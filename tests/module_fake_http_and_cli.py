import hug


@hug.get()
@hug.CLIRouter()
def made_up_go():
    return "Going!"
