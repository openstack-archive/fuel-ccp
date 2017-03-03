#!/usr/bin/env python
import argparse
import os
import sys
import yaml

CCP_DEFAULTS = "../../fuel_ccp/resources/defaults.yaml"
YAML_DUMP = {
    'width': float("inf"),
    'line_break': 0,
    'default_flow_style': False,
    'default_style': '"'
}

if __name__ == "__main__":
    curr_dir = os.path.dirname(os.path.realpath(__file__))
    parser = argparse.ArgumentParser()
    f = os.path.join(curr_dir, CCP_DEFAULTS)
    default_config = os.path.normpath(f)
    parser.add_argument('--defaults-file', default=default_config,
                        help="Set different location for configuration file")
    parser.add_argument('--update-defaults', action='store_true',
                        help="Inplace update of config file with backup")
    args = parser.parse_args()
    if not os.path.isfile(args.defaults_file):
        sys.exit("%s is not a valid file" % args.defaults_file)

    try:
        with open(os.path.join(curr_dir, CCP_DEFAULTS), 'r') as f:
            before = yaml.load(f.read())
        with open(os.path.join(curr_dir, 'server-key.pem'), 'r') as f:
            server_key = f.read()
        with open(os.path.join(curr_dir, 'server.pem'), 'r') as f:
            server_crt = f.read()
        with open(os.path.join(curr_dir, 'ca.pem'), 'r') as f:
            ca = f.read()
        a = before['configs']['security']['tls']
        a['server_key'] = server_key
        a['server_cert'] = server_crt
        a['ca_cert'] = ca
        if args.update_defaults:
            os.rename(args.defaults_file, args.defaults_file + '.bak')
            with open(args.defaults_file, 'w') as f:
                yaml.dump(before, f, **YAML_DUMP)
        else:
            print(yaml.dump(before, **YAML_DUMP))
    except IOError as e:
        print(e)
        sys.exit("Try generating certificates first")
