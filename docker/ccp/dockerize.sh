#!/bin/bash

# The script, which is going to create fuel-ccp docker image out of current content of the working
# tree or from specific branch of remote git repository
set -e

usage() {
    cat << EOF
    Usage: $0 [-u] [-r REPO] [-b BRANCH]

    -h   Prints this help
    -u   Build image from default upstream git repository
    -r   Repository to create image from
    -b   Branch to use for docker assembly

    By default docker image will be created from the local source tree. If flag -u is set, sources
    will be fetched from upstream git repository "https://git.openstack.org/openstack/fuel-ccp".
    Arbitrary repository REPO can be specified with -r flag.
    Flag -b can be used to ccp state from the branch other than master. In this case branch BRANCH will be
    checked out from the selected repository before assembling docker container.
EOF
}

build_tarball() {
    echo "Creating sdist tarball"
    python setup.py sdist
    TARBALL_NAME=`find dist -type f -iname "*.tar.gz" -printf '%T@ %p\n' | sort -n | tail -1 | cut -f2- -d" "`
}

SOURCE_REPO_DEFAULT=https://git.openstack.org/openstack/fuel-ccp
TMP_TAR=fuel-ccp.tar.gz
# Using local source tree by default.
SOURCE_REPO=`readlink -f ../../`

while getopts ":ur:b:h" opt; do
    case $opt in
        r)
            SOURCE_REPO="${OPTARG}"
            ;;
        b)
            BRANCH="${OPTARG}"
            ;;
        h)
            usage
            exit 1
            ;;
        u)
            SOURCE_REPO="${SOURCE_REPO_DEFAULT}"
            ;;
        \?)
            echo "Invalid option: -${OPTARG}" >&2
            usage
            exit 1
            ;;
        :)
            echo "Option -${OPTARG} requires an argument." >&2
            usage
            exit 1
            ;;
    esac
done

function cleanup {
    if [ -e "${SRC_DIR}" ]; then
        rm -rf "${SRC_DIR}"
        echo "Deleted temp working directory $SRC_DIR"
    fi
    if [ -e "${TMP_TAR}" ]; then
        rm "${TMP_TAR}"
        echo "Deleting sources archive ${TMP_TAR}"
    fi
}
trap cleanup EXIT

SRC_DIR=`mktemp -d "/tmp/ccp_sources.XXXXXXXXX"`
pushd "${SRC_DIR}"

echo "Fetching sources from ${SOURCE_REPO}"
git clone "${SOURCE_REPO}"
cd fuel-ccp
if [ -n "${BRANCH}" ]; then
    echo "Checking out branch ${BRANCH}"
    git checkout -b "${BRANCH}" origin/"${BRANCH}"
fi

build_tarball
popd
cp "${SRC_DIR}"/fuel-ccp/"${TARBALL_NAME}" "${TMP_TAR}"

echo "Building Docker image"
docker build -t fuel-ccp .
