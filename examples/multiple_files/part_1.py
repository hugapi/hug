import hug


@hug.get()
def part1():
    """This view will be at the path ``/part1``"""
    return "part1"
