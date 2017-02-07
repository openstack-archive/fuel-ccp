# -*- coding: utf-8 -*-

# Copyright 2010-2011 OpenStack Foundation
# Copyright (c) 2013 Hewlett-Packard Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from oslotest import base
import six

from fuel_ccp.config import _yaml
from fuel_ccp.tests import conf_fixture


class TestCase(base.BaseTestCase):
    """Test case base class for all unit tests."""

    def setUp(self):
        super(TestCase, self).setUp()
        self.conf = self.useFixture(conf_fixture.Config()).conf

    def nested_dict_to_attrdict(self, d):
        if isinstance(d, dict):
            return _yaml.AttrDict({k: self.nested_dict_to_attrdict(v)
                                   for k, v in six.iteritems(d)})
        elif isinstance(d, list):
            return list(map(self.nested_dict_to_attrdict, d))
        else:
            return d
