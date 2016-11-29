FROM debian:jessie
MAINTAINER MOS Microservices <mos-microservices@mirantis.com>

ENV DEBIAN_FRONTEND=noninteractive \
    GOSU_VERSION=1.9

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
COPY fuel-ccp.tar.gz /opt/

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python \
        python-pip \
        python-dev \
        python-netaddr \
        software-properties-common \
        python-setuptools \
        gcc \
        git \
# Bringing GOSU to be able to execute ccp process under current user
    && apt-get install -y --no-install-recommends ca-certificates wget \
    && dpkgArch="$(dpkg --print-architecture | awk -F- '{ print $NF }')" \
    && wget -O /usr/local/bin/gosu "https://github.com/tianon/gosu/releases/download/$GOSU_VERSION/gosu-$dpkgArch" \
    && wget -O /usr/local/bin/gosu.asc "https://github.com/tianon/gosu/releases/download/$GOSU_VERSION/gosu-$dpkgArch.asc" \
    && export GNUPGHOME="$(mktemp -d)" \
    && gpg --keyserver ha.pool.sks-keyservers.net --recv-keys B42F6819007F00F88E364FD4036A9C25BF357DD4 \
    && gpg --batch --verify /usr/local/bin/gosu.asc /usr/local/bin/gosu \
    && rm -r "$GNUPGHOME" /usr/local/bin/gosu.asc \
    && chmod +x /usr/local/bin/gosu \
    && gosu nobody true \
# Installing Fuel CCP
    && pip install /opt/fuel-ccp.tar.gz && rm /opt/fuel-ccp.tar.gz \
    && chmod a+x /usr/local/bin/entrypoint.sh \
# Cleaning up a bit
    && apt-get purge -y --auto-remove wget gcc \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
