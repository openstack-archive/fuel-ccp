from oslo_config import cfg


CONF = cfg.CONF
kubernetes_opts = [
    cfg.StrOpt('server',
               default='http://localhost:8080',
               help='The URL for the Kubernetes API server'),
    cfg.StrOpt('namespace',
               default='ccp',
               help='The name of the namespace'),
    cfg.StrOpt('ca-cert',
               help='The location of the CA certificate file'),
    cfg.StrOpt('key-file',
               help='The location of the key file'),
    cfg.StrOpt('cert-file',
               help='The location of the certificate file'),
    cfg.BoolOpt('insecure',
                help='Disable certificate checking')
]
kubernetes_opt_group = cfg.OptGroup(name='kubernetes',
                                    title='Kubernetes client')
CONF.register_group(kubernetes_opt_group)
CONF.register_cli_opts(kubernetes_opts, kubernetes_opt_group)
CONF.register_cli_opts(kubernetes_opts, kubernetes_opt_group)

DEFAULTS = {
    'kubernetes': {
        'server': '127.0.0.1:8080',
        'namespace': 'ccp',
        'ca_certs': None,
        'key_file': None,
        'cert_file': None,
        'insecure': None,
    },
}

SCHEMA = {
    'kubernetes': {
        'type': 'object',
        'additionalProperties': False,
        'properties': {
            'server': {'type': 'string'},
            'namespace': {'type': 'string'},
            'ca_cert': {'anyOf': [{'type': 'string'}, {'type': 'null'}]},
            'key_file': {'anyOf': [{'type': 'string'}, {'type': 'null'}]},
            'cert_file': {'anyOf': [{'type': 'string'}, {'type': 'null'}]},
            'insecure': {'anyOf': [{'type': 'string'}, {'type': 'null'}]},
        },
    },
}
