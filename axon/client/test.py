#!/usr/bin/env python
# Copyright (c) 2019 VMware, Inc. All Rights Reserved.
# SPDX-License-Identifier: BSD-2 License
# The full license information can be found in LICENSE.txt
# in the root directory of this project.

import time

from axon.client.traffic_elements import TrafficRule, \
    Endpoint, Port, Protocol, Action, Connected
from axon.client.basic_traffic_controller import BasicTrafficController


rule_list = list()


rule_list.append(
    TrafficRule(Endpoint('10.172.50.40'), Endpoint('10.172.50.40'),
                Port(12345), Protocol.UDP, Connected.CONNECTED,
                Action.ALLOW)
)

start = time.time()
controller = BasicTrafficController()
controller.register_traffic(rule_list)
controller.restart_traffic()
end = time.time()
