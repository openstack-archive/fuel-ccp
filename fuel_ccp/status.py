from fuel_ccp import kubernetes

def show_status():
    deployments = kubernetes.list_cluster_deployments()
    daemonsets = kubernetes.list_cluster_daemonsets()
    import pdb; pdb.set_trace()
