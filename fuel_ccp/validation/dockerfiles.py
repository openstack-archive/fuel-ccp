from oslo_log import log as logging

from fuel_ccp import build
from fuel_ccp import config

LOG = logging.getLogger(__name__)


def validate():
    # We ensure that all images' parents are in our repos here
    dockerfiles = build.get_dockerfiles_tree()
    LOG.info("Dockerfile tree has been built successfully, no template issues"
             " or bad image_spec's")
    # Now we ensure that no unexpected orphat (base) images are found
    # (i.e. images with malformed FROM line)
    base_images = config.CONF.images.base_images
    for dockerfile in dockerfiles.values():
        name = dockerfile['name']
        parent = dockerfile['parent']
        should_have_parent = name not in base_images
        has_parent = parent is not None
        if has_parent and not should_have_parent:
            raise RuntimeError(
                'Image {} is listed as base image but has a parent {}'.format(
                    name, parent))
        if not has_parent and should_have_parent:
            raise RuntimeError(
                'Image {} doesn\'t have a parent and is not listed as base'
                ' image. Malformed FROM line?'.format(name, parent))
    LOG.info("All Dockerfiles have been verified successfully")
