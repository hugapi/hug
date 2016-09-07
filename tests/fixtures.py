"""Defines fixtures that can be used to streamline tests and / or define dependencies"""
from random import randint

import pytest

import hug


@pytest.fixture
def hug_api():
    """Defines a dependency for and then includes a uniquely identified hug API for a single test case"""
    return hug.API('fake_api_{}'.format(randint(0, 1000000)))
