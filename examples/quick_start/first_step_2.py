"""First hug API (local and HTTP access)"""
import hug


@hug.get(examples='name=Timothy&age=26')
@hug.local()
def happy_birthday(name: hug.types.text, age: hug.types.number, hug_timer=3):
    """Says happy birthday to a user"""
    return {'message': 'Happy {0} Birthday {1}!'.format(age, name),
            'took': float(hug_timer)}
