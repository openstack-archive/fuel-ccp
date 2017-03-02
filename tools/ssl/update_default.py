#!/usr/bin/env python
import sys
import yaml

CCP_DEFAULTS = "../../fuel_ccp/resources/defaults.yaml"

if __name__ == "__main__":
    try:
        with open(CCP_DEFAULTS, 'r') as defaults, \
            open('server-key.pem', 'r') as server_key, \
            open('server.pem', 'r') as server_crt, \
            open('ca.pem', 'r') as ca_crt:  # noqa
                before = yaml.load(defaults.read())
                a = before['configs']['security']['tls']
                a['server_key'] = server_key.read()
                a['server_cert'] = server_crt.read()
                a['ca_cert'] = ca_crt.read()
                print(yaml.dump(before, width=float("inf"), line_break=0,
                      default_flow_style=False, default_style='"'))
    except IOError as e:
        print(e)
        sys.exit("Try generating certificates first")
