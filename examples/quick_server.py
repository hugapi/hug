import hug


@hug.get()
def quick():
    return 'Serving!'


if __name__ == '__main__':
    __hug__.serve()  # noqa
