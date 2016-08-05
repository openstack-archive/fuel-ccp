import os
import re
import yaml

from oslo_config import cfg
from oslo_log import log as logging
from pykwalify import core


CONF = cfg.CONF

LOG = logging.getLogger(__name__)

YAML_FILE_RE = re.compile(r'\.yaml$')


ROLE_SCHEMA_OBJECT = """
    schema;t_not_empty_string:
        type: str
        range:
            min: 1

    schema;t_not_empty_string_array:
        type: seq
        range:
            min: 1

        sequence:
            include: t_not_empty_string

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
            include: t_command

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
                    type: map
                    range:
                        min: 1

                        mapping:
                            regex;(^[0-1]{1,5}$):
                                type: int
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
                        type: map

                        mapping:
                            name:
                                include: t_not_empty_string
                                required: True
                            image:
                                include: t_not_empty_string
                                required: True
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
                                    type: map

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
                            regex;(^[a-zA-Z0-9][a-zA-Z\_0-9\.-]*$):
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
                                        pattern: [0-7]{4,4}
                                    user:
                                        include: t_not_empty_String
"""


def validate(type):
    if type == "service_def":
        validate_service_def_for_repos()
    else:
        raise RuntimeError("Unexpected validation type")


def validate_service_def_for_repos():
    repos = CONF.repositories.names

    for repo in repos:
        validate_service_def_for_repo(repo)


def validate_service_def_for_repo(repo):
    service_dir = os.path.join(CONF.repositories.path, repo, 'service')

    if not os.path.isdir(service_dir):
        return

    for service_file in os.listdir(service_dir):
        if YAML_FILE_RE.search(service_file):
            LOG.debug("Parse role file: %s", service_file)
            with open(os.path.join(service_dir, service_file), "r") as f:
                role_obj = yaml.load(f)
                validate_service_def(role_obj)


def validate_service_def(service_def):
    c = core.Core(source_data=service_def, schema_files=ROLE_SCHEMA_OBJECT)
    c.validate(raise_exception=True)
