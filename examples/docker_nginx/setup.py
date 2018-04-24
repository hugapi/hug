# pylint: disable=C0326
""" Base setup script """

from setuptools import setup

setup(
    name = "app-name",
    version = "0.0.1",
    description = "App Description",
    url = "https://github.com/CMoncur/nginx-gunicorn-hug",
    author = "Cody Moncur",
    author_email = "cmoncur@gmail.com",
    classifiers = [
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        "Development Status :: 3 - Alpha",
        "Programming Language :: Python :: 3.6"
    ],
    packages = [],

    # Entry Point
    entry_points = {
        "console_scripts": []
    },

    # Core Dependencies
    install_requires = [
        "hug"
    ],

    # Dev/Test Dependencies
    extras_require = {
        "dev": [],
        "test": [],
    },

    # Scripts
    scripts = []
)
