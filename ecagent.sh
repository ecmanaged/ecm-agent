#!/bin/sh

SHOW_USAGE=0
set -x 

if [ $# -eq 2 ]; then
    if [ $1 = "--configure-uuid" ]; then
        ./ecm_configure.py $2
    else
        SHOW_USAGE=1
    fi
fi

if [ $# -gt 2 -o $# -eq 1 -o $SHOW_USAGE -eq 1 ]; then
    echo "Usage:"
    echo "$0 [--configure-uuid UUID]"
    echo ""
    echo "If the optional argument UUID is specified, the agent will be"
    echo "reconfigured with this UUID and a random new password will be created."
    exit 1
fi

twistd  -ny ecagentd.tac
