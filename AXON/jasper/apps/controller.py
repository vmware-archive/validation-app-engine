#!/usr/bin/env python
# Copyright (c) 2020 VMware, Inc. All Rights Reserved.
# SPDX-License-Identifier: BSD-2 License
# The full license information can be found in LICENSE.txt
# in the root directory of this project.

'''
Traffic Controller App handles all the pre processing and post processing
work for Traffic Generation.
'''

import logging

from axon.apps.base import BaseApp

import jasper.traffic.core as core
import jasper.traffic.task as task

from axon.common.config import NAMESPACE_INTERFACE_NAME_PREFIXES
from axon.utils.network_utils import NamespaceManager, InterfaceManager

from jasper.traffic.manager import ClientManager, ServerManager
from jasper.utils.common import get_mgmt_ifname, get_host_name


log = logging.getLogger(__name__)


class TrafficControllerApp(BaseApp):

    def __init__(self, record_queue, rulesApp):
        super(TrafficControllerApp, self).__init__()

        self._recore_queue = record_queue
        self.rules = rulesApp

        # TODO : Following should be consumed through Global Apps actually.
        # Namespace Manager handles all namespace information fetching.
        self._ns_mgr = NamespaceManager()
        # Interface Manager
        self._if_mgr = InterfaceManager()
        # Endpoint - Target Map. A target can be host, Namespace or
        # a container.

        # Host is where this app is running. Based on host,
        # it is decided for a rule if we need to run a client
        # or server.
        ifname = get_mgmt_ifname()
        self._host = self._if_mgr.get_interface(ifname)['address']
        self._update_endpoints_map()

        self._client_mgr = ClientManager(self._recore_queue)
        self._server_mgr = ServerManager()

    @property
    def host(self):
        return self._host

    def _update_endpoints_map(self):
        self._ep_map = {}

        # Update Interfaces on this host
        host_target = core.VMHost(name=get_host_name(),
                                  ip=self.host)

        # To support local traffic.
        self._ep_map['127.0.0.1'] = host_target
        self._ep_map['::1'] = host_target

        for ifname in self._if_mgr.get_all_interfaces():
            if not any([ifname.startswith(x) for x in NAMESPACE_INTERFACE_NAME_PREFIXES]):
                continue
            interface = self._if_mgr.get_interface(ifname)
            self._ep_map[interface['address']] = host_target

        # Update Namespaces on this host.
        for ns_name, ns_interfaces in self._ns_mgr.get_namespace_interface_map().items():
            ns_target = core.NSHost(name=ns_name, ip=self.host)
            for interface in ns_interfaces:
                self._ep_map[interface['address']] = ns_target

    def discover_interfaces(self):
        """ Re/Discovers insterfaces """
        self._if_mgr._discover_interfaces()
        self._ns_mgr.discover_namespaces()
        self._update_endpoints_map()

    def _add_rule_info(self, trule):
        trule.src_target = self._ep_map.get(trule.src)
        trule.dst_target = self._ep_map.get(trule.dst)
        trule.src_host = self.host if trule.src_target else None
        trule.dst_host = self.host if trule.dst_target else None

        if not trule.src_host and not trule.dst_host:
            log.error("Invalid request to add rule (%s) on host %s",
                      trule, self.host)
            return

        # Set Active/Inactive State
        trule.state = getattr(trule, 'state', core.TrafficRule.ACTIVE)

        # Add server on this host if needed. Start server before the client.
        if trule.dst_host:
            self._server_mgr.add_task(trule)

        # Add client on this host if needed.
        if trule.src_host:
            self._client_mgr.add_task(trule)

    def _get_traffic_rule(self, rule):
        """ Rule config. """
        trule = core.TrafficRule()

        for key, val in rule.items():
            setattr(trule, key, val)

        self._add_rule_info(trule)
        return trule

    def register_traffic(self, traffic_rules=None):
        for rule in traffic_rules:
            # create a rule and add it to database.
            trule = self._get_traffic_rule(rule)
            self.rules.add(trule)

    def start(self, ruleid):
        """ Start a Traffic task (again). """
        self._client_mgr.start(ruleid)

    def stop(self, ruleid):
        """ Stop a Traffic task. """
        self._client_mgr.stop(ruleid)

    def close(self):
        self._client_mgr.close()
        self._server_mgr.close()
