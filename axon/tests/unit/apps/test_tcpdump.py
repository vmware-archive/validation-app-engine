#!/usr/bin/env python
# Copyright (c) 2020 VMware, Inc. All Rights Reserved.
# SPDX-License-Identifier: BSD-2 License
# The full license information can be found in LICENSE.txt
# in the root directory of this project.
'''
Unit test for PCAP app.
'''
import logging
import unittest

from axon.apps.tcpdump import TCPDump


log = logging.getLogger(__name__)


class TestTCPDumpApp(unittest.TestCase):

    def setUp(self):
        super(TestTCPDumpApp, self).setUp()
        self._app = TCPDump()

    def test_tcpdump(self):
        """
        """
        _data = [
                ('p1.pcap', 'eth0', ''),
                ('p2.pcap', 'l0', ''),
                ('p3.pcap', 'virbr0', ''),
                ('p4.pcap', 'eth1', '')]

        # start running tcpdump for interfaces
        for dst, interface, args in _data:
            self._app.start_pcap(dst_file=dst, interface=interface,
                                 args=args)

        # some of these won't start as interface might not exist.
        # stop those processes.
        for dst, _, _ in _data:
            if not self._app.is_running(dst):
                self._app.stop_pcap(dst)

        # stop the app. Should stop all the packet capture.
        self._app.stop()

        msg = "Packet capture still going"
        assert all(not self._app.is_running(dst) for dst, _, _ in _data), msg
