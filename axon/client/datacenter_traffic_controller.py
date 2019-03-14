#!/usr/bin/env python
# Copyright (c) 2019 VMware, Inc. All Rights Reserved.
# SPDX-License-Identifier: BSD-2 License
# The full license information can be found in LICENSE.txt
# in the root directory of this project.

import os
import logging
import pickle
from multiprocessing.pool import ThreadPool

from axon.client.traffic_controller import TrafficController, TrafficRecord
from axon.client.axon_client import AxonClient

WORKLOAD_VIF_MAP_FILE_PATH = "/var/lib/axon/workloadvifs/"
WORKLOAD_VIF_MAP_FILE = "workload_vif_map.pkl"
log = logging.getLogger(__name__)


def register_traffic(register_param):
    workload_server = register_param[0]
    rule_list = register_param[1]
    proxy_host = register_param[2]
    with AxonClient(workload_server, proxy_host=proxy_host) as client:
        for rule in rule_list:
            client.traffic.register_traffic([rule.as_dict()])


def start_servers(start_param):
    server = start_param[0]
    proxy_host = start_param[1]
    with AxonClient(server, proxy_host=proxy_host) as client:
        client.traffic.start_servers()


def start_clients(start_param):
    server = start_param[0]
    proxy_host = start_param[1]
    with AxonClient(server, proxy_host=proxy_host) as client:
        client.traffic.start_clients()


def stop_servers(stop_param):
    server = stop_param[0]
    proxy_host = stop_param[1]
    with AxonClient(server, proxy_host=proxy_host) as client:
        client.traffic.stop_servers()


def stop_clients(stop_param):
    server = stop_param[0]
    proxy_host = stop_param[1]
    with AxonClient(server, proxy_host=proxy_host) as client:
        client.traffic.stop_clients()


class WorkloadVifsMap(object):
    def __init__(self):
        self.vif_map_load = False

    def build_workloads_vifs_map(self, workload_ips=[]):
        """
        This function build workloads_vifs_map based on workload_ips and
        dumps this
        :param workload_ips:
        :return: workload_vif_map
        """
        if not workload_ips:
            return "No Workload IPs passed to build workloads vifs map"
        map_dict = {}
        for wip in workload_ips:
            with AxonClient(wip) as client:
                map_dict.update({nm_ip: wip for nm_ip in
                                 client.namespace.list_namespaces_ips()})

        self.dump_workloads_vifs_map(map_dict)

    def set_workloads_vifs_map(self, workload_vif_map):
        """
        This function directly dumps workloads_vifs_map
        :param workload_vif_map:
        :return:
        """
        # TODO decide workload_vif_map pattern from the user
        self.dump_workloads_vifs_map(workload_vif_map)

    def load_workloads_vifs_map(self):
        log.info("Loading workloads_vifs map")
        with open(os.path.join(
                WORKLOAD_VIF_MAP_FILE_PATH, WORKLOAD_VIF_MAP_FILE)) as wv_map:
            self.workload_vif_map = pickle.loads(wv_map.read())
            self.vif_map_load = True

    def dump_workloads_vifs_map(self, map_obj):
        if not os.path.isdir(WORKLOAD_VIF_MAP_FILE_PATH):
            os.makedirs(WORKLOAD_VIF_MAP_FILE_PATH)
        workload_vifs_file = os.path.join(WORKLOAD_VIF_MAP_FILE_PATH,
                                          WORKLOAD_VIF_MAP_FILE)
        os.remove(workload_vifs_file) if os.path.exists(workload_vifs_file) \
            else None
        log.info("Saving workloads_vifs map %r " % (workload_vifs_file))
        with open(workload_vifs_file, 'wb') as fd:
            pickle.dump(map_obj, fd)


class DataCenterTrafficController(TrafficController):
    """
    This TrafficController deals with On-prem traffic
    """
    def __init__(self, gateway_host=None):
        super(DataCenterTrafficController, self).__init__()
        self._gw_host = gateway_host
        self._workload_servers = dict()
        self._servers = dict()
        self.__map_obj = WorkloadVifsMap()
        self.__map_obj.load_workloads_vifs_map()

    def get_associated_workload(self, vif):
        if self.__map_obj.vif_map_load:
            return self.__map_obj.workload_vif_map.get(vif)

    def register_traffic(self, traffic_config):
        for trule in traffic_config:
            src_vif = str(trule.src_eps.ip_list[0])
            dst_vif = str(trule.dst_eps.ip_list[0])

            src_traffic_record = TrafficRecord(src_vif)
            src_traffic_record.add_client(trule.protocol, trule.port.port,
                                          dst_vif, trule.connected,
                                          trule.action)
            dst_traffic_record = TrafficRecord(dst_vif)
            dst_traffic_record.add_server(trule.protocol, trule.port.port)

            workload_src = self.get_associated_workload(src_vif)
            workload_dst = self.get_associated_workload(dst_vif)
            src = workload_src if workload_src else src_vif
            dst = workload_dst if workload_dst else dst_vif
            # src
            if not self._workload_servers.get(src):
                self._workload_servers[str(src)] = [src_traffic_record]
            else:
                self._workload_servers[str(src)].append(src_traffic_record)

            # dst
            if not self._workload_servers.get(str(dst)):
                self._workload_servers[dst] = [dst_traffic_record]
            else:
                self._workload_servers[dst].append(dst_traffic_record)

        pool = ThreadPool(50)
        params = [(workload_server, rule_list, self._gw_host) for
                  workload_server, rule_list in
                  self._workload_servers.items()]
        pool.map(register_traffic, params)
        pool.close()
        pool.join()

    def unregister_traffic(self, traffic_config):
        pass

    def __stop_clients(self, servers):
        servers = servers if servers else self._workload_servers.keys()
        if not servers:
            return
        pool = ThreadPool(50)
        params = [(server, self._gw_host) for server in servers]
        pool.map(stop_clients, params)
        pool.close()
        pool.join()

    def __stop_servers(self, servers):
        servers = servers if servers else self._workload_servers.keys()
        if not servers:
            return
        pool = ThreadPool(50)
        params = [(server, self._gw_host) for server in servers]
        pool.map(stop_servers, params)
        pool.close()
        pool.join()

    def __start_servers(self, servers):
        servers = servers if servers else self._workload_servers.keys()
        if not servers:
            return
        pool = ThreadPool(50)
        params = [(server, self._gw_host) for server in servers]
        pool.map(start_servers, params)
        pool.close()
        pool.join()

    def __start_clients(self, servers):
        servers = servers if servers else self._workload_servers.keys()
        if not servers:
            return
        pool = ThreadPool(50)
        params = [(server, self._gw_host) for server in servers]
        pool.map(start_clients, params)
        pool.close()
        pool.join()

    def stop_traffic(self, servers=None):
        self.__stop_clients(servers)
        self.__stop_servers(servers)

    def start_traffic(self, servers=None):
        self.__start_servers(servers)
        self.__start_clients(servers)

    def restart_traffic(self, servers=None):
        self.stop_traffic(servers)
        self.start_traffic(servers)
