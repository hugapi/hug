import hug
import part_1
import part_2


@hug.get("/")
def say_hi():
    """This view will be at the path ``/``"""
    return "Hi from root"


@hug.extend_api()
def with_other_apis():
    """Join API endpoints from two other modules

    These will be at ``/part1`` and ``/part2``, the paths being automatically
    generated from function names.

    """
    return [part_1, part_2]
