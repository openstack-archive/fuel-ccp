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

from fuel_ccp.tests import conf_fixture


class TestCase(base.BaseTestCase):
    """Test case base class for all unit tests."""

    def setUp(self):
        super(TestCase, self).setUp()
        self.conf = self.useFixture(conf_fixture.Config()).conf

    def assertRaisesWithMessageIn(self, exc, msg, func, *args, **kwargs):
        try:
            func(*args, **kwargs)
            self.fail('Exception "{0}" raised.'.format(exc))
        except Exception as inst:
            self.assertIsInstance(inst, exc)
            self.assertIn(msg, str(inst))
