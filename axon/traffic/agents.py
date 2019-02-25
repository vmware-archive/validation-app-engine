#!/usr/bin/env python
# Copyright (c) 2019 VMware, Inc. All Rights Reserved.
# SPDX-License-Identifier: BSD-2 License
# The full license information can be found in LICENSE.txt
# in the root directory of this project.

import logging

from axon.traffic.connected_state import ConnectedStateProcessor, \
    DBConnectedState
from axon.traffic.manager import RootNsServerManager, NamespaceServerManager,\
    NamespaceClientManager, RootNsClientManager
from axon.utils.network_utils import NamespaceManager, InterfaceManager
import axon.common.config as axon_config


class AxonRootNamespaceServerAgent(object):
    """
    Launch Servers in Root Namespace
    """

    def __init__(self):
        self.mngrs_map = {}
        self.connected_state = ConnectedStateProcessor(DBConnectedState())
        self._primary_ep = None
        self._if_manager = InterfaceManager()
        self.log = logging.getLogger(__name__)

    @property
    def primary_endpoint(self):
        """
        Get the primary endpoint address from the DB
        It assumes in non namespace mode there will be
        only single interface.
        """
        if not self._primary_ep:
            endpoints = self.connected_state.get_connected_state()
            if endpoints:
                self._primary_ep = endpoints[0]['endpoint']
        return self._primary_ep

    def start_servers(self, namespace='root'):
        """
        Start Set of default servers
        :return: None
        """
        if not self.primary_endpoint:
            self.log.warning("Server will not be started since "
                             "no connected state exists yet")
            return
        mngr = RootNsServerManager() if not \
            self.mngrs_map.get(namespace) else self.mngrs_map.get(namespace)
        servers = self.connected_state.get_servers(self.primary_endpoint)
        servers = servers if servers else []
        for proto, port in servers:
            mngr.start_server(proto, port, self.primary_endpoint)
        self.mngrs_map[namespace] = mngr

    def stop_servers(self, namespace='root'):
        """
        Stop all Servers
        :return: None
        """
        for mngr in self.mngrs_map.values():
            mngr.stop_all_servers()

    def add_server(self, port, protocol, endpoint, namespace='root'):
        """
        Run a Server in a root namespace
        :param port: port on which server will listen
        :type port: int
        :param protocol: protocol on which server will listen
        :type protocol: str
        :return: None
        """
        interface = self._if_manager.get_interface_by_ip(endpoint)
        if not interface:
            self.log.error("No interface fount with IP %s on host" % endpoint)
            return
        mngr = RootNsServerManager() if not \
            self.mngrs_map.get(namespace) else self.mngrs_map.get(namespace)
        mngr.start_server(protocol, port, endpoint)
        self.connected_state.create_or_update_connected_state(
            endpoint, [(protocol, port)])
        self.mngrs_map[namespace] = mngr

    def list_servers(self):
        server_list = []
        for mngr in self.mngrs_map.values():
            server_list.extend(mngr.list_servers())
        return server_list

    def get_server(self, protocol, port):
        server_list = []
        for mngr in self.mngrs_map.values():
            server_list.extend(mngr.get_server(protocol, port))
        return server_list

    def stop_server(self, protocol, port, namespace='root'):
        for mngr in self.mngrs_map.values():
            mngr.stop_server(port, protocol)


class AxonNameSpaceServerAgent(AxonRootNamespaceServerAgent):
    """
    Launch Servers in different namespaces
    """

    def __init__(self, ns_list=None, ns_interface_map=None):
        super(AxonNameSpaceServerAgent, self).__init__()
        self._ns_list = ns_list
        self._ns_iterface_map = ns_interface_map
        self._setup()

    def _setup(self):
        if not self._ns_list or not self._ns_iterface_map:
            mngr = NamespaceManager()
            self._ns_list = mngr.get_all_namespaces()
            self._ns_iterface_map = mngr.get_namespace_interface_map()

    def start_servers(self, namespace=None):
        """
        Start a set of default server in given namespace
        :param namespace: namespace name
        :type namespace: str
        :return: None
        """
        ns_list = [namespace] if namespace else self._ns_list
        for ns in ns_list:
            interfaces = self._ns_iterface_map.get(ns)
            interface = [iface for iface in interfaces for prefix in
                         axon_config.NAMESPACE_INTERFACE_NAME_PREFIXES
                         if prefix in iface.name]
            if not interface:
                continue
            src = interface[0].address
            servers = self.connected_state.get_servers(src)
            if not servers:
                continue
            ns_mngr = NamespaceServerManager(ns) if not \
                self.mngrs_map.get(ns) else self.mngrs_map.get(ns)
            for proto, port in servers:
                ns_mngr.start_server(proto, port, src)
            self.mngrs_map[ns] = ns_mngr

    def stop_servers(self, namespace=None):
        """
        Stop all server in given namespace
        :return: None
        """
        ns_list = [namespace] if namespace else self._ns_list
        for ns, mngr in self.mngrs_map.items():
            if ns in ns_list:
                mngr.stop_all_servers()

    def add_server(self, port, protocol, endpoint, namespace=None):
        """
        Run a Server in a given namespace
        :param port: port on which server will listen
        :type port: int
        :param protocol: protocol on which server will listen
        :type protocol: str
        :param namespace: namespace name
        :type namespace: str
        :return: None
        """
        ns_list = [namespace] if namespace else self._ns_list
        for ns in ns_list:
            ns_mngr = NamespaceServerManager(ns) if not \
                self.mngrs_map.get(ns) else self.mngrs_map.get(ns)
            interfaces = self._ns_iterface_map.get(ns)
            interface = [iface for iface in interfaces for prefix in
                         axon_config.NAMESPACE_INTERFACE_NAME_PREFIXES
                         if prefix in iface.name]
            if not interface:
                continue
            src = interface[0].address
            ns_mngr.start_server(protocol, port, src)
            self.connected_state.create_or_update_connected_state(
                src, [(protocol, port)])
            self.mngrs_map[ns] = ns_mngr

    def stop_server(self, protocol, port, namespace=None):
        ns_list = [namespace] if namespace else self._ns_list
        for ns in ns_list:
            server_mngr = self.mngrs_map.get(ns)
            if server_mngr:
                server_mngr.stop_server(port, protocol)


class AxonRootNamespaceClientAgent(object):
    """
    Launch Servers in Root Namespace
    """
    def __init__(self):
        self.mngrs_map = {}
        self.connected_state = ConnectedStateProcessor(DBConnectedState())
        self._primary_ep = None
        self.log = logging.getLogger(__name__)

    # TODO(Pradeep Singh) MOve below code to a common location
    @property
    def primary_endpoint(self):
        """
        Get the primary endpoint address from the DB
        It assumes in non namespace mode there will be
        only single interface.
        """
        if not self._primary_ep:
            endpoints = self.connected_state.get_connected_state()
            if endpoints:
                self._primary_ep = endpoints[0]['endpoint']
        return self._primary_ep

    def start_clients(self):
        if not self.primary_endpoint:
            self.log.warning("Clients will not be started since "
                             "no connected state exists yet")
            return
        clients = self.connected_state.get_clients(self.primary_endpoint)
        clients = clients if clients else []
        if clients:
            mngr = RootNsClientManager() if not \
                self.mngrs_map.get('localhost') else \
                self.mngrs_map.get('localhost')
            mngr.start_client(self.primary_endpoint, clients)
            self.mngrs_map['localhost'] = mngr

    def stop_clients(self, namespace='localhost'):
        """
        Stop all Clients
        :return: None
        """
        for mngr in self.mngrs_map.values():
            mngr.stop_clients()

    def stop_client(self, namespace='localhost'):
        for mngr in self.mngrs_map.values():
            mngr.stop_client()


class AxonNameSpaceClientAgent(AxonRootNamespaceClientAgent):
    """
    Launch Servers in different namespaces
    """

    def __init__(self, ns_list=None, ns_iterface_map=None):
        super(AxonNameSpaceClientAgent, self).__init__()
        self._ns_list = ns_list
        self._ns_iterface_map = ns_iterface_map
        self._setup()

    def _setup(self):
        if not self._ns_list or not self._ns_iterface_map:
            mngr = NamespaceManager()
            self._ns_list = mngr.get_all_namespaces()
            self._ns_iterface_map = mngr.get_namespace_interface_map()

    def start_clients(self, namespace=None):
        ns_list = [namespace] if namespace else self._ns_list
        for ns in ns_list:
            interfaces = self._ns_iterface_map.get(ns)
            interface = [iface for iface in interfaces for prefix in
                         axon_config.NAMESPACE_INTERFACE_NAME_PREFIXES
                         if prefix in iface.name]
            if not interface:
                continue
            src = interface[0].address
            clients = self.connected_state.get_clients(src)
            if not clients:
                continue
            ns_mngr = NamespaceClientManager(ns) if not \
                self.mngrs_map.get(ns) else \
                self.mngrs_map.get(ns)
            ns_mngr.start_client(src, clients)
            self.mngrs_map[ns] = ns_mngr

    def stop_clients(self, namespace=None):
        ns_list = [namespace] if namespace else self._ns_list
        for ns, mngr in self.mngrs_map.items():
            if ns in ns_list:
                mngr.stop_clients()

    def stop_client(self, namespace=None):
        namespace = self._ns_iterface_map.get(namespace)
        if namespace:
            ns_mngr = self.mngrs_map.get(namespace)
            if ns_mngr:
                ns_mngr.stop_client()
