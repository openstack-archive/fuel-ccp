#!/bin/bash

# The script, which is going to create fuel-ccp docker image out of current content of the working
# tree or from specific branch of remote git repository
set -e

usage() {
    cat << EOF
    Usage: $0 [-r] [-b BRANCH]

    -h   Prints this help
    -r   Build image from remote git repository
    -b   Branch in the upstream repository to create image from.

    By default docker image will be created from the local source tree. If flag -r is set, sources
    will be fetched from remote git repository "https://git.openstack.org/openstack/fuel-ccp".
    Optionally branch in the remote repository can be specified with -b flag.
EOF
}

build_tarball() {
    echo "Creating sdist tarball"
    python setup.py sdist
    TARBALL_NAME=`ls -t dist | head -n 1`
}

FUEL_CCP_REPO=https://git.openstack.org/openstack/fuel-ccp

while getopts ":rb:h" opt; do
    case $opt in
        r)
            REMOTE="1"
            ;;
        b)
            BRANCH="$OPTARG"
            ;;
        h)
            usage
            exit 1
            ;;
        \?)
            echo "Invalid option: -$OPTARG" >&2
            usage
            exit 1
            ;;
        :)
            echo "Option -$OPTARG requires an argument." >&2
            usage
            exit 1
            ;;
    esac
done

if [[ -z "$REMOTE" && -n "$BRANCH" ]]; then
    echo "Option -b cannot be used without -r"
    usage
    exit 1
fi

if [ -n "$REMOTE" ]; then
    echo "Fetching sources from remote repo $FUEL_CCP_REPO"
    SRC_DIR=`mktemp -d "/tmp/ccp_sources.XXXXXXXXX"`

    function cleanup {
        rm -rf "$SRC_DIR"
        echo "Deleted temp working directory $SRC_DIR"
    }
    trap cleanup EXIT

    pushd $SRC_DIR
    git clone $FUEL_CCP_REPO
    cd fuel-ccp
    if [ -n "$BRANCH" ]; then
        echo "Checking out branch $BRANCH"
        git checkout -b $BRANCH origin/$BRANCH
    fi
    build_tarball
    popd
    cp $SRC_DIR/fuel-ccp/dist/$TARBALL_NAME fuel-ccp.tar.gz
else
    echo "Using local sources to create tarball"
    build_tarball
    cp dist/$TARBALL_NAME fuel-ccp.tar.gz
fi

echo "Building Docker image"
docker build -f docker/ccp/Dockerfile -t fuel-ccp .
rm fuel-ccp.tar.gz

