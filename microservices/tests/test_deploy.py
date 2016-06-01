from oslo_config import cfg

from microservices import deploy
from microservices.tests import base

CONF = cfg.CONF


class TestDeploy(base.TestCase):
    def test_fill_cmd(self):
        workflow = {}
        cmd = {
            "command": "ps",
            "user": "bart"
        }
        deploy._fill_cmd(workflow, cmd)
        self.assertDictEqual({"command": "ps", "user": "bart"}, workflow)

    def test_fill_cmd_without_user(self):
        workflow = {}
        cmd = {"command": "ps"}
        deploy._fill_cmd(workflow, cmd)
        self.assertDictEqual({"command": "ps"}, workflow)

    def test_expand_files(self):
        service = {
            "daemon": {
                "command": "ps",
                "files": ["conf1"]
            },
            "pre": [
                {"files": ["conf2"], "command": "cmd"}
            ],
            "post": [
                {"files": ["conf3"], "command": "cmd"}
            ]
        }
        files = {
            "conf1": {
                "path": "/etc/syslog.conf",
                "content": "pig"
            },
            "conf2": {
                "path": "/spam",
                "content": "eggs"
            },
            "conf3": {
                "path": "/lelik",
                "content": "bolik"
            }
        }
        deploy._expand_files(service, files)
        expected = {
            "daemon": {
                "command": "ps",
                "files": {
                    "conf1": {
                        "path": "/etc/syslog.conf",
                        "content": "pig"
                    }
                }
            },
            "pre": [
                {
                    "files": {
                        "conf2": {
                            "path": "/spam",
                            "content": "eggs"
                        }
                    },
                    "command": "cmd"
                }
            ],
            "post": [
                {
                    "files": {
                        "conf3": {
                            "path": "/lelik",
                            "content": "bolik"
                        }
                    },
                    "command": "cmd"
                }
            ]
        }
        self.assertDictEqual(expected, service)
