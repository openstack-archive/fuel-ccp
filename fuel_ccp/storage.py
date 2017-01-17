import logging

from fuel_ccp import config
from fuel_ccp import kubernetes
from fuel_ccp import templates


CONF = config.CONF
LOG = logging.getLogger(__name__)


class GlusterFS(object):
    VOLUME_TYPE = "glusterfs"
    SECRET_NAME = "glusterfs-key"

    def __init__(self, conf):
        self.conf = conf

    def configure(self):
        if not self.conf.storage.glusterfs["enable"]:
            LOG.info("GlusterFS is disabled in config, skipping initial"
                     " configuration")
            return

        self._create_volume_claim()
        self._create_storage_class()
        if self.conf.storage.glusterfs["auth"]["enable"]:
            self._configure_auth()

    def _create_volume_claim(self):
        spec = templates.serialize_volume_claim(self.VOLUME_TYPE)
        kubernetes.process_object(spec)

    def _create_storage_class(self):
        spec = kubernetes.serialize_storage_class(self.VOLUME_TYPE)
        spec["provisioner"] = "kubernetes.io/glusterfs"
        parameters = {
            "resturl": self.conf.storage.glusterfs["url"],
            "restauthenable": str(
                self.conf.storage.glusterfs["auth"]["enable"]).lower()
        }
        if self.conf.storage.glusterfs["auth"]["enable"]:
            parameters["restuser"] = (
                self.conf.storage.glusterfs["auth"]["username"])
            parameters["secretNamespace"] = self.conf.configs["namespace"]
            parameters["secretName"] = self.SECRET_NAME
        spec["parameters"] = parameters
        kubernetes.process_object(spec)


    def _configure_auth(self):
        spec = templates.serialize_secret(
            name=self.SECRET_NAME,
            type="kubernetes.io/glusterfs",
            data={"key": self.conf.storage.glusterfs["auth"]["password"]}
        )
        kubernetes.process_object(spec)


def init_storage_backends():
    GlusterFS(CONF).configure()
