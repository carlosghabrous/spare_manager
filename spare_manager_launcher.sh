#!/bin/sh

# Production
USER_HOME=/user/pclhc
PYTHON_HOME=${USER_HOME}/bin/python

if [ -f ${USER_HOME}/.profile ]; then 
    . /user/pclhc/.profile
else
    . ${USER_HOME}/.bash_profile
fi

PYTHON_VENV_ACTIVE=0
SM_HOME=${PYTHON_HOME}/spare_manager
SM_VENV_DIR_NAME=spare_mgr_venv
SM_DIR_NAME=spare_manager

is_python_venv_active()
{
    PYTHON_COMMAND="import sys; sys.stdout.write('1')\
    if hasattr(sys, 'sys.real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)\
    else sys.stdout.write('0')"

    PYTHON_VENV_ACTIVE=$(python3 -c "$PYTHON_COMMAND")
}

if [ $# -ne 1 ]; then
    echo "Missing input argument [-c|-a]"
    exit
fi

source deactivate
is_python_venv_active

if [ "${PYTHON_VENV_ACTIVE}" != 1 ]; then
    echo "Activating spare manager virtual environment..."
    source ${SM_HOME}/${SM_VENV_DIR_NAME}/bin/activate
fi

if [ "$1" = "-c" ]; then 
    python3 ${SM_HOME}/${SM_VENV_DIR_NAME}/lib64/python3.6/site-packages/${SM_DIR_NAME}/sm_main.py -c &
elif [ "$1" == "-a" ]; then 
    python3 ${SM_HOME}/${SM_VENV_DIR_NAME}/lib64/python3.6/site-packages/${SM_DIR_NAME}/sm_main.py -a &
else
    echo "Unrecognized argument! Valid arguements: -c|-a"
    exit
fi

pm_pid=$!

trap "kill $pm_pid; wait $pm_pid" SIGHUP SIGINT SIGTERM
#EOF