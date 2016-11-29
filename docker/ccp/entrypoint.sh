#!/bin/bash

# Adds a local user
# Either use the LOCAL_USER_ID and LOCAL_USER_NAME if passed in at runtime
# or user with id 9001 and name ccp as a fallback

USER_ID=${LOCAL_USER_ID:-9001}
USER_NAME=${LOCAL_USER_NAME:-ccp}

groupadd docker -g `stat -c " %g" /var/run/docker.sock`
useradd --shell /bin/bash -u $USER_ID -G docker -o -m $USER_NAME 2> /dev/null
export HOME=/home/$USER_NAME
chown $USER_NAME:$USER_NAME $HOME
cd $HOME && exec /usr/local/bin/gosu $USER_NAME ccp "$@"
