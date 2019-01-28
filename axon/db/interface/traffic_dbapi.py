#!/usr/bin/env python
# Copyright (c) 2019 VMware, Inc. All Rights Reserved.
# SPDX-License-Identifier: BSD-2 License
# The full license information can be found in LICENSE.txt
# in the root directory of this project.

"""
This module acts as an interface between the database storgae for AddOnTraffic
infromation and its processing engines.
"""
from collections import defaultdict as ddict
import json

import axon.db.backends.models.traffic_models as traffic_models


class PortAlreadyUsed(Exception):
    pass


class AddOnTrafficRecord(object):
    def __init__(self, endpoint, servers=None, clients=None):
        self.endpoint = endpoint

        self.servers = ddict(list) if servers is None else servers
        self.clients = [ddict(list), ddict(list)
                        ] if clients is None else clients

        self.modified = False

    def add_server(self, protocol, port):
        used_ports = set()
        for key, value in self.servers.items():
            used_ports = used_ports.union(value)

        if port not in used_ports:
            if protocol not in self.servers.keys():
                self.servers[protocol] = []
            self.servers[protocol].append(port)
            self.modified = True

    def add_client(self, server, protocol, port, action):
        used_ports = []
        for client in self.clients:
            for protocol, dsts in client.items():
                for _server, _port in dsts:
                    used_ports.append((_server, _port))

        if (server, port) not in used_ports:
            index = 0 if not action else 1
            if protocol not in self.clients[index].keys():
                self.clients[index][protocol] = []

            self.clients[index][protocol].append((server, port))
            self.modified = True

    def remove_server(self, protocol, port):
        if protocol in self.servers.keys() and port in self.servers[protocol]:
            self.servers[protocol].remove(port)
            self.modified = True

    def remove_client(self, server, protocol, port, action):
        for client in self.clients:
            for _protocol, dsts in client.items():
                if protocol != _protocol:
                    continue
                if [server, port] in dsts:
                    dsts.remove([server, port])
                    self.modified = True

    def get_servers(self):
        return json.dumps(self.servers)

    def get_clients(self):
        return json.dumps(self.clients)

    def __repr__(self):
        return '{"%s":{"servers":%s, "clients":%s} }' % (
            self.endpoint, json.dumps(self.servers), json.dumps(self.clients))


class AddOnTrafficDB(object):
    def register_traffic(self, trule):
        try:
            # We may also want to run only servers at the endpoint.
            if trule.src_eps:
                # If source is specified for the rule, we must specify
                # if traffic is expected from this
                self.add_client(trule)
            # Add server type and protocol to run on the destination endpoint.
            self.add_server(trule.dst_eps, trule.protocol, trule.port)
        except Exception:
            pass

    def unregister_traffic(self, trule):
        try:
            # We may also want to run only servers at the endpoint.
            if trule.src_eps:
                # If source is specified for the rule, we must specify
                # if traffic is expected from this
                self.remove_client(trule)
            # Add server type and protocol to run on the destination endpoint.
            self.remove_server(trule.dst_eps, trule.protocol, trule.port)
        except Exception:
            pass

    def restart_traffic(self, ep=None, servers=False, clients=False):
        """
        Restart the traffic on the endpoint. Restart server or client
        only.
        """
        pass


class AddOnTrafficMock(AddOnTrafficDB):
    def __init__(self):
        """
        This class mocks the database for AddOnTraffic records with in-memory
        simulator. It is useful for unit testing of APIs and database schema.

        TODO: Move this to unit test case before the final merge.
        """

        # ideally the table should be represented by a list
        # but we are using dict here for faster seatch.
        self.tg_rules = ddict(AddOnTrafficRecord)

    def add_server(self, ep, protocol, port):
        self.tg_rules[ep].add_server(protocol, port)

    def add_client(self, traffic_rule):
        src = traffic_rule.src
        dst = traffic_rule.dst
        protocol = traffic_rule.protocol
        port = traffic_rule.port
        action = traffic_rule.action

        self.tg_rules[src].add_client(dst, protocol, port, action)


class AddOnTrafficRiakRecord(AddOnTrafficRecord):
    def __init__(self, riak_rec):
        endpoint = riak_rec.vif_id
        servers = json.loads(riak_rec.servers) if riak_rec.servers else None
        clients = json.loads(riak_rec.clients) if riak_rec.clients else None

        super(AddOnTrafficRiakRecord, self).__init__(endpoint, servers,
                                                     clients)

    def update(self):
        """
        Updates the Riak for the corresponding Record object.
        """
        if not self.modified:
            return
        # Make sure current record is updated otherwise it will overwrite
        # the record in database.
        rec = traffic_models.TrafficConfig(vif_id=self.endpoint)
        rec.servers = json.dumps(self.servers)
        rec.clients = json.dumps(self.clients)
        # dbuffer.Buffer(rec).write()


class AddOnTrafficRiak(AddOnTrafficDB):
    def __init__(self):
        """
        This class implements the DB interface layer for Riak for AddOnTraffic
        records.
        """
        super(AddOnTrafficRiak, self).__init__()

    def _get_record(self, endpoint):
        rec = traffic_models.TrafficConfig(vif_id=endpoint)
        # data = dbuffer.Buffer(rec).read()
        data = None
        if data:
            assert (len(data) == 1)
            rec = AddOnTrafficRiakRecord(data[0])
        else:
            rec = AddOnTrafficRiakRecord(rec)

        return rec

    def add_server(self, ep, protocol, port):
        port = port.port if hasattr(port, 'port') else port
        for ipaddr in ep.ip_list:
            ipaddr = '%s' % ipaddr
            rec = self._get_record(ipaddr)
            rec.add_server(protocol, port)
            rec.update()

    def add_client(self, trule):
        for ipaddr in trule.src_eps.ip_list:
            ipaddr = '%s' % ipaddr
            rec = self._get_record(ipaddr)
            for dst in trule.dst_eps.ip_list:
                rec.add_client('%s' % dst, trule.protocol, trule.port.port,
                               trule.action)
            rec.update()

    def remove_server(self, ep, protocol, port):
        port = port.port if hasattr(port, 'port') else port
        for ipaddr in ep.ip_list:
            ipaddr = '%s' % ipaddr
            rec = self._get_record(ipaddr)
            rec.remove_server(protocol, port)
            rec.update()

    def remove_client(self, trule):
        for ipaddr in trule.src_eps.ip_list:
            ipaddr = '%s' % ipaddr
            rec = self._get_record(ipaddr)
            for dst in trule.dst_eps.ip_list:
                rec.remove_client('%s' % dst, trule.protocol, trule.port.port,
                                  trule.action)
            rec.update()
