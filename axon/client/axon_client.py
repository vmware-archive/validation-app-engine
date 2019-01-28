#!/usr/bin/env python
# Copyright (c) 2019 VMware, Inc. All Rights Reserved.
# SPDX-License-Identifier: BSD-2 License
# The full license information can be found in LICENSE.txt
# in the root directory of this project.

import rpyc

rpyc.core.protocol.DEFAULT_CONFIG['allow_pickle'] = True


class Manager(object):
    def __init__(self, client):
        self._client = client


class TrafficManger(Manager):

    def add_server(self, protocol, port, endpoint, namespace=None):
        self._client.traffic.add_server(protocol, port, endpoint, namespace)

    def start_clients(self):
        self._client.traffic.start_clients()

    def get_traffic_config(self, endpoint=None):
        return self._client.traffic.get_traffic_config(endpoint)

    def register_traffic(self, traffic_rules):
        return self._client.traffic.register_traffic(traffic_rules)

    def unregister_traffic(self, traffic_rules):
        self._client.traffic.unregister_traffic(traffic_rules)

    def list_servers(self):
        return self._client.traffic.list_servers()

    def get_server(self, protocol, port):
        return self._client.traffic.get_server(protocol, port)

    def stop_servers(self, namespace=None):
        self._client.traffic.stop_servers(namespace)

    def start_servers(self, namespace=None):
        return self._client.traffic.start_servers(namespace)

    def stop_server(self, protocol, port, namespace=None):
        self._client.traffic.stop_server(protocol, port, namespace)

    def stop_client(self, src):
        self._client.traffic.stop_client(src)

    def stop_clients(self, namespace=None):
        self._client.traffic.stop_clients(namespace)


class StatsManager(Manager):

    def get_failure_count(self, start_time=None, end_time=None,
                          destination=None, port=None):
        return self._client.stats.get_failure_count(
            start_time=start_time, end_time=end_time,
            destination=destination, port=port)

    def get_success_count(self, start_time=None, end_time=None,
                          destination=None, port=None):
        return self._client.stats.get_success_count(
            start_time=start_time, end_time=end_time,
            destination=destination, port=port)

    def get_failures(self, start_time=None, end_time=None,
                     destination=None, port=None):
        return self._client.stats.get_failures(
            start_time=start_time, end_time=end_time,
            destination=destination, port=port)


class NamespaceManager(Manager):

    def list_namespaces(self):
        return self._client.namespace.list_namespaces()

    def get_namespace(self, name):
        return self._client.namespace.get_namespace(name)

    def list_namespaces_ips(self):
        return self._client.namespace.list_namespaces_ips()


class InterfaceManager(Manager):

    def list_interfaces(self):
        return self._client.interface.list_interfaces()

    def get_interface(self, name):
        return self._client.interface.get_interface(name)


class AxonClient(object):
    """
    Top level object to access Axon API
    """

    def __init__(self, axon_host, axon_port=5678, proxy_host=None):
        """ Initialization of Client object

        :param axon_host: the host IP where axon service is running
        :type axon_host: str
        :param axon_port: port on which axon is listening
        :type axon_port: int
        :param proxy_host: ip of the proxy host
        :type proxy_host: str
        """
        self._host = axon_host
        self._port = axon_port
        if proxy_host:
            conn = rpyc.classic.connect(proxy_host)
            self.rpc_client = conn.modules.rpyc.connect(self._host, self._port)
        else:
            self.rpc_client = rpyc.connect(self._host, self._port)
        self.traffic = TrafficManger(self.rpc_client.root)
        self.stats = StatsManager(self.rpc_client.root)
        self.namespace = NamespaceManager(self.rpc_client.root)
        self.interface = InterfaceManager(self.rpc_client.root)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.rpc_client.close()
