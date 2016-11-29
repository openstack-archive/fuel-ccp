FROM debian:jessie
MAINTAINER MOS Microservices <mos-microservices@mirantis.com>

ENV DEBIAN_FRONTEND noninteractive

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
    && apt-get clean \
    && rm -rf /tmp/* /var/tmp/*

COPY fuel-ccp.tar.gz /opt/

RUN pip install /opt/fuel-ccp.tar.gz && rm /opt/fuel-ccp.tar.gz

ENTRYPOINT ["ccp"]
