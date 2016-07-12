def k8s_name(*args):
    return "-".join(tuple(args)).replace("_", "-")
