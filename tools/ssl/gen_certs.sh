#!/usr/bin/env bash
# More detailed instructions:
# https://coreos.com/os/docs/latest/generate-self-signed-certificates.html

cfssl=`which cfssl`
cfssljson=`which cfssljson`

if [ ! -x "$cfssl" ] || [ ! -x "$cfssljson" ]; then
    echo "cfssl or cfssljson not found in PATH"
    echo "You can install them using the following commands:"
    echo -e "\t go get -u github.com/cloudflare/cfssl/cmd/cfssl"
    echo -e "\t go get -u github.com/cloudflare/cfssl/cmd/cfssljson"
    echo "Or any suitable package manager (brew, apt)"
    exit 1
fi

if [ -f "ca.pem"  ]; then
    echo "CA certificate already present, refusing to overwrite it"
else
    $cfssl gencert -initca ca-csr.json | $cfssljson -bare ca
fi

if [ -f "server.pem" ]; then
    echo "Server certificate already exists, refusing to overwrite it"
else
    $cfssl gencert -config=ca-config.json -ca=ca.pem -ca-key=ca-key.pem server.json | $cfssljson -bare server
fi
