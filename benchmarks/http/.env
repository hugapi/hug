#!/bin/bash
OPEN_PROJECT_NAME="hug_benchmark_http"

if [ "$PROJECT_NAME" = "$OPEN_PROJECT_NAME" ]; then
    return
fi

if [ ! -f ".env" ]; then
    return
fi

export PROJECT_NAME=$OPEN_PROJECT_NAME
export PROJECT_DIR="$PWD"
export PROJECT_VERSION="1.0.0"

if [ ! -d "venv" ]; then
     if ! hash pyvenv 2>/dev/null; then
        function pyvenv()
        {
            if hash pyvenv-3.5 2>/dev/null; then
                pyvenv-3.5 $@
            fi
            if hash pyvenv-3.4 2>/dev/null; then
                pyvenv-3.4 $@
            fi
            if hash pyvenv-3.3 2>/dev/null; then
                pyvenv-3.3 $@
            fi
            if hash pyvenv-3.2 2>/dev/null; then
                pyvenv-3.2 $@
            fi
        }
    fi

    echo "Making venv for $PROJECT_NAME"
    pyvenv venv
    . venv/bin/activate
    pip install -r requirements.txt
fi

. venv/bin/activate

# Quick directory switching
alias root="cd $PROJECT_DIR"


function run {
    (root
     . runner.sh)
}


function update {
    pip install -r requirements.txt
}


function leave {
    export PROJECT_NAME=""
    export PROJECT_DIR=""

    unalias root

    unset -f run
    unset -f update

    unset -f leave

    deactivate
}
