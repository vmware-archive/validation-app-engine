#!/usr/bin/env python
# Copyright (c) 2020 VMware, Inc. All Rights Reserved.
# SPDX-License-Identifier: BSD-2 License
# The full license information can be found in LICENSE.txt
# in the root directory of this project.
'''
A simple test case for sending traffic.
'''

import logging
import os
import queue
import time
import unittest
import uuid

from jasper.apps.rules import RulesApp
from jasper.apps.controller import TrafficControllerApp
from jasper.apps.results import Results
from jasper.apps.recorder import RecordManager


log = logging.getLogger(__name__)


class TrafficAppTest(unittest.TestCase):
    DB_FILE = 'test_traffic_rules.db'
    MAX_QUEUE_SIZE = 20000

    DUMMY_RULE = {
        'reqid': '%s' % uuid.uuid4(),
        'ruleid': '%s' % uuid.uuid4(),
        'src': '127.0.0.1',
        'dst': '127.0.0.1',
        'protocol': 'TCP',
        'port': 9465,
        'connected': True
    }

    def setUp(self):
        if os.path.exists(self.DB_FILE):
            os.remove(self.DB_FILE)

        self.records = queue.Queue(self.MAX_QUEUE_SIZE)
        self.rulesApp = RulesApp(db_file=self.DB_FILE)
        self.controller = TrafficControllerApp(self.records, self.rulesApp)
        self.results = Results()
        self.db_pool = RecordManager(self.records)
        self.db_pool.start()

    def test_traffic(self):
        traffic_rules = [self.DUMMY_RULE]

        self.controller.register_traffic(traffic_rules)

        time.sleep(10)  # Wait for taffic to run for 10 seconds.
        records = self.results.traffic(self.DUMMY_RULE['reqid'])
        assert records, "Traffic results missing"

    def tearDown(self):
        self.controller.close()
        self.db_pool.close()
        self.rulesApp.close()
        os.remove(self.DB_FILE)
