import pkg_resources

import microservices


def k8s_name(*args):
    return "-".join(tuple(args)).replace("_", "-")


def get_resource_path(path):
    return pkg_resources.resource_filename(
        microservices.version_info.package, path)
