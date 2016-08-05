import os
import re
import yaml

from oslo_config import cfg
from oslo_log import log as logging
from pykwalify import core


CONF = cfg.CONF

LOG = logging.getLogger(__name__)

YAML_FILE_RE = re.compile(r'\.yaml$')


SERVICE_SCHEMA_YAML = """
schema;t_not_empty_string:
    type: str
    range:
        min: 1

schema;t_not_empty_string_array:
    type: seq
    range:
        min: 1

    sequence:
      - include: t_not_empty_string

schema;t_command:
    type: map
    mapping:
        name:
            include: t_not_empty_string
            required: True
        command:
            include: t_not_empty_string
            required: True
        dependencies:
            include: t_not_empty_string_array
        type:
            type: str
            enum: ["single", "local"]
        files:
            include: t_not_empty_string_array
        user:
            include: t_not_empty_string
schema;t_not_empty_command_array:
    type: seq
    range:
        min: 1

    sequence:
      - include: t_command

type: map
mapping:
    service:
        type: map
        required: True

        mapping:
            name:
                include: t_not_empty_string
                required: True
            ports:
                type: seq
                range:
                    min: 1

                sequence:
                  - type: str
                    pattern: ^[\w]+(:[\w]+)?$
            daemonset:
                type: bool
            host-net:
                type: bool
            containers:
                type: seq
                required: True
                range:
                    min: 1

                sequence:
                  - type: map

                    mapping:
                        name:
                            include: t_not_empty_string
                            required: True
                        image:
                            include: t_not_empty_string
                            required: True
                        privileged:
                            type: bool
                        probes:
                            type: map

                            mapping:
                                readiness:
                                    include: t_not_empty_string
                                liveness:
                                    include: t_not_empty_string
                        volumes:
                            type: seq
                            range:
                                min: 1

                            sequence:
                              - type: map

                                mapping:
                                    name:
                                        include: t_not_empty_string
                                        required: True
                                    type:
                                        type: str
                                        enum: ["host", "empty-dir"]
                                    path:
                                        include: t_not_empty_string
                                    mount-path:
                                        include: t_not_empty_string
                                    readOnly:
                                        type: bool
                        pre:
                            include: t_not_empty_command_array
                        daemon:
                            include: t_command
                        post:
                            include: t_not_empty_command_array
    files:
        type: map

        mapping:
            regex;(^[\w][\w.-]*$):
                type: map

                mapping:
                    path:
                        include: t_not_empty_string
                        required: true
                    content:
                        include: t_not_empty_string
                        required: true
                    perm:
                        type: str
                        pattern: "[0-7]{3,4}"
                    user:
                        include: t_not_empty_String
"""

SERVICE_SCHEMA = yaml.load(SERVICE_SCHEMA_YAML)


def validate(objects):
    if not objects:
        objects = ["services"]

    for object in set(objects):
        if object == "services":
            validate_services_for_repos()
        else:
            raise RuntimeError(
                "Unexpected object: {}".format(object)
            )


def validate_services_for_repos():
    repos = CONF.repositories.names

    for repo in repos:
        validate_services_for_repo(repo)


def validate_services_for_repo(repo):
    service_dir = os.path.join(CONF.repositories.path, repo, 'service')

    if not os.path.isdir(service_dir):
        LOG.warning("Repository '%s' doesn't contain 'service' directory. "
                    "Skip validation for service files")
        return

    for service_file in os.listdir(service_dir):
        if YAML_FILE_RE.search(service_file):
            LOG.debug("Parse role file: %s", service_file)
            with open(os.path.join(service_dir, service_file), "r") as f:
                service = yaml.load(f)
                validate_service(service)


def validate_service(service):
    c = core.Core(source_data=service, schema_data=SERVICE_SCHEMA)
    c.validate(raise_exception=True)
