FROM debian:latest
MAINTAINER MOS Microservices <mos-microservices@mirantis.com>

ENV DEBIAN_FRONTEND noninteractive

RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get dist-upgrade -y \
    && apt-get install -y --no-install-recommends \
        python \
        python-pip \
        python-dev \
        python3-dev \
        python-netaddr \
        software-properties-common \
        python-setuptools \
        gcc \
        git \
    && apt-get clean

ADD fuel-ccp.tar /opt/fuel-ccp/

RUN pip install /opt/fuel-ccp/ && rm -rf /opt/fuel-ccp/

ENTRYPOINT ["ccp"]
