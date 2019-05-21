"""First API, local access only"""
import hug


@hug.LocalRouter()
def happy_birthday(name: hug.types.text, age: hug.types.number, hug_timer=3):
    """Says happy birthday to a user"""
    return {"message": "Happy {0} Birthday {1}!".format(age, name), "took": float(hug_timer)}
