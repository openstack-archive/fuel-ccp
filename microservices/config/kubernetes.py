from oslo_config import cfg


CONF = cfg.CONF
kubernetes_opts = [
    cfg.StrOpt('server',
               default='',
               help='Addres and port for kube-apiserver')
]
kubernetes_opt_group = cfg.OptGroup(name='kubernetes',
                                    title='Kubernetes client')
CONF.register_group(kubernetes_opt_group)
CONF.register_cli_opts(kubernetes_opts, kubernetes_opt_group)
CONF.register_cli_opts(kubernetes_opts, kubernetes_opt_group)
