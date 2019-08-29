"""This example demonstrates how to perform different kinds of redirects using hug"""
import hug


@hug.get()
def sum_two_numbers(number_1: int, number_2: int):
    """I'll be redirecting to this using a variety of approaches below"""
    return number_1 + number_2


@hug.post()
def internal_redirection_automatic(number_1: int, number_2: int):
    """This will redirect internally to the sum_two_numbers handler
       passing along all passed in parameters.

       This kind of redirect happens internally within hug, fully transparent to clients.
    """
    print("Internal Redirection Automatic {}, {}".format(number_1, number_2))
    return sum_two_numbers


@hug.post()
def internal_redirection_manual(number: int):
    """Instead of normal redirecting: You can manually call other handlers, with computed parameters
       and return their results
    """
    print("Internal Redirection Manual {}".format(number))
    return sum_two_numbers(number, number)


@hug.post()
def redirect(redirect_type: hug.types.one_of(("permanent", "found", "see_other")) = None):
    """Hug also fully supports classical HTTP redirects,
       providing built in convenience functions for the most common types.
    """
    print("HTTP Redirect {}".format(redirect_type))
    if not redirect_type:
        hug.redirect.to("/sum_two_numbers")
    else:
        getattr(hug.redirect, redirect_type)("/sum_two_numbers")


@hug.post()
def redirect_set_variables(number: int):
    """You can also do some manual parameter setting with HTTP based redirects"""
    print("HTTP Redirect set variables {}".format(number))
    hug.redirect.to("/sum_two_numbers?number_1={0}&number_2={0}".format(number))
