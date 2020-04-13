#!/usr/bin/env python
# Copyright (c) 2019 VMware, Inc. All Rights Reserved.
# SPDX-License-Identifier: BSD-2 License
# The full license information can be found in LICENSE.txt
# in the root directory of this project.

import mock
import multiprocessing as mp

from axon.tests import base as test_base
from axon.traffic.clients.clients import TrafficClient


class TestTCPClient(test_base.BaseTestCase):
    """
    Test for TCPClient utilities
    """

    @mock.patch('socket.socket')
    def test_tcp_traffic_client(self, mock_socket):
        source = '1.2.3.4'
        destinations = [('TCP', 12345, '1.2.3.5', True, 1)]
        record_queue = mp.Queue(2)
        _traffic_client = TrafficClient(
            source, destinations, record_queue)
        _traffic_client._send_traffic()

    @mock.patch('socket.socket')
    def test_udp_traffic_client(self, mock_socket):
        source = '1.2.3.4'
        destinations = [('UDP', 12345, '1.2.3.5', True, 1)]
        record_queue = mp.Queue(2)
        _traffic_client = TrafficClient(
            source, destinations, record_queue)
        _traffic_client._send_traffic()
