import hug


@hug.cli()
def add(numbers: list = None):
    return sum([int(number) for number in numbers])


if __name__ == "__main__":
    add.interface.cli()
