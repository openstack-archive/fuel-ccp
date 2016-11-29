#!/bin/bash
tar cf fuel-ccp.tar * .git
docker build -f docker/ccp/Dockerfile -t fuel-ccp .
rm fuel-ccp.tar
