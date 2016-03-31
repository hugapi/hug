#! /bin/bash

 if [[ "$TRAVIS_OS_NAME" == "osx" ]]; then

    # enable pyenv shims to activate the proper python version
    eval "$(pyenv init -)"

    # Log some information on the environment
    pyenv local
    which python
    which pip
    python --version
    python -m pip --version
fi
