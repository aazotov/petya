#!/bin/bash

DISPLAY=:1
export DISPLAY

SERVICE='skyperem.py'
 
if ps ax | grep -v grep | grep $SERVICE > /dev/null
then
    echo `date` "script is already running, OK"
else
    DISPLAY=:0
    export DISPLAY
    echo $DISPLAY
    echo "No script found"
    pwd
    cd /srv/petya/petya_linux
    python skyperem.py >> /srv/petya/petya.log 2>&1 &
fi
