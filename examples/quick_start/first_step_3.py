"""First hug API (local, command-line, and HTTP access)"""
import hug


@hug.CLIRouter()
@hug.get(examples="name=Timothy&age=26")
@hug.LocalRouter()
def happy_birthday(name: hug.types.text, age: hug.types.number, hug_timer=3):
    """Says happy birthday to a user"""
    return {"message": "Happy {0} Birthday {1}!".format(age, name), "took": float(hug_timer)}


if __name__ == "__main__":
    happy_birthday.interface.cli()
