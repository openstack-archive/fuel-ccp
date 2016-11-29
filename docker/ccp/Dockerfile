FROM debian:jessie
MAINTAINER MOS Microservices <mos-microservices@mirantis.com>

ENV DEBIAN_FRONTEND=noninteractive \
    GOSU_VERSION=1.9

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
COPY fuel-ccp.tar.gz /opt/

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
        python \
        python-dev \
        gcc \
        git \
# Bringing GOSU to be able to execute ccp process under current user
    && dpkgArch="$(dpkg --print-architecture | awk -F- '{ print $NF }')" \
    && curl -L -o /usr/local/bin/gosu "https://github.com/tianon/gosu/releases/download/$GOSU_VERSION/gosu-$dpkgArch" \
    && curl -L -o /usr/local/bin/gosu.asc "https://github.com/tianon/gosu/releases/download/$GOSU_VERSION/gosu-$dpkgArch.asc" \
    && export GNUPGHOME="$(mktemp -d)" \
    && gpg --keyserver ha.pool.sks-keyservers.net --recv-keys B42F6819007F00F88E364FD4036A9C25BF357DD4 \
    && gpg --batch --verify /usr/local/bin/gosu.asc /usr/local/bin/gosu \
    && rm -r "$GNUPGHOME" /usr/local/bin/gosu.asc \
    && chmod +x /usr/local/bin/gosu \
    && gosu nobody true \
# Installing pip and virtualenv
    && curl -O https://bootstrap.pypa.io/get-pip.py \
    && python get-pip.py --user \
    && ~/.local/bin/pip install --user virtualenv \
# Creating venv for CCP
    && ~/.local/bin/virtualenv /var/lib/ccp/venv \
# Installing Fuel CCP
    && /var/lib/ccp/venv/bin/pip install /opt/fuel-ccp.tar.gz \
    && chmod a+x /usr/local/bin/entrypoint.sh \
# Cleaning up a bit
    && apt-get purge -y --auto-remove curl gcc \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
              /tmp/* /var/tmp/* \
              get-pip.py \
              ~/.local/

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
