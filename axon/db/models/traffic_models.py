#!/usr/bin/env python
# Copyright (c) 2019 VMware, Inc. All Rights Reserved.
# SPDX-License-Identifier: BSD-2 License
# The full license information can be found in LICENSE.txt
# in the root directory of this project.

"""
This contains models to replicate functionality in the old connectivity
queries found in lib/test/infrastructure/connectivity.py. It also
alters the returned data to make them protocol independent
"""
import time
import uuid

import axon.db.models.base_model as drecord
from axon.db.models.base_model import Column


class Fault(drecord.TimestampedRecord):
    """
    This records a fault between a pair of endpoints
    """
    index = True
    usetype = True
    src = Column(indexed=True)
    dst = Column(indexed=True)
    connected = Column(column_type=bool, indexed=True)
    protocol = Column(indexed=True)


class RequestCounts(drecord.MapRecord):
    """
    This maintains a pair of crdt counters noting successes and failures.
    The key is the integral floor of the timestamp this class is set to
    readonly since the data for it comes from creating success of failure
    records above
    """
    created = Column(
        column_type=int, indexed=True, schema_name='created_register')
    success_connected = Column(
        column_type=int,
        indexed=False,
        schema_name='success_connected_counter',
        default=0)
    success_disconnected = Column(
        column_type=int,
        indexed=False,
        schema_name='success_disconnected_counter',
        default=0)
    failed_connected = Column(
        column_type=int,
        indexed=False,
        schema_name='failed_connected_counter',
        default=0)
    failed_disconnected = Column(
        column_type=int,
        indexed=False,
        schema_name='failed_disconnected_counter',
        default=0)

    @property
    def count(self):
        """
        Returns the total observations seen in this second
        """
        return sum((self.success_connected, self.success_disconnected,
                    self.failed_connected, self.failed_disconnected))

    @property
    def connectivity(self):
        """
        This returns the percentage of successful requests out of the total
        requests in this interval
        """
        success_count = sum((self.success_connected,
                             self.success_disconnected))
        if self.count > 0:
            return float(success_count) / float(self.count)
        else:
            return 0.0


class LatencyStats(drecord.MapRecord):
    """
    This maintains a pair of crdt counters noting the sum of latencies in
    milliseconds and the number of samples.
    """
    created = Column(
        column_type=int, indexed=True, schema_name='created_register')
    latency_sum = Column(
        column_type=int,
        indexed=True,
        schema_name='latency_sum_counter',
        default=0)
    samples = Column(
        column_type=int,
        indexed=True,
        schema_name='samples_counter',
        default=0)

    @property
    def latency(self):
        """
        Returns the total observations seen in this second
        """
        if self.latency_sum > 0 and self.samples > 0:
            return float(self.latency_sum) / float(self.samples)
        else:
            return float('inf')


class Category(drecord.MapRecord):
    """
    Categories are defined as paths and protocol specifications
    """
    category_id = Column(
        indexed=True,
        schema_name='category_id_register',
        default=lambda: str(uuid.uuid4()),
        key_col=True)
    created = Column(
        column_type=int, indexed=False, schema_name='created_register')
    path = Column(indexed=True, schema_name='path_register')
    protocol = Column(indexed=True, schema_name='protocol_register')
    active = Column(
        column_type=bool,
        indexed=True,
        default=True,
        schema_name='active_flag')
    disconnected = Column(
        column_type=bool,
        indexed=True,
        default=False,
        schema_name='disconnected_flag')
    successes = Column(
        column_type=int,
        indexed=False,
        schema_name='successes_counter',
        default=0)
    samples = Column(
        column_type=int,
        indexed=False,
        schema_name='samples_counter',
        default=0)

    @property
    def key(self):
        """
        Key these by category id
        """
        return self.category_id


# class Network(drecord.SearchRecord):
#     """
#     This defines a network realized in test topology
#     """
#     nw_ip = Column(indexed=True)
#     start_ip = Column()
#     end_ip = Column()
#     unused_ips = Column(column_type=list, default=list)
#     network_id = Column(
#         indexed=True, default=lambda: str(uuid.uuid4()), key_col=True)

#     @property
#     def key(self):
#         """
#         Key these by network_id
#         """
#         return self.network_id


# class CategoryNetworkMap(drecord.SearchRecord):
#     """
#     This defines mapping between category and networks
#     """
#     category_id = Column(indexed=True, key_col=True)
#     src_network_ip = Column(indexed=True, key_col=True)
#     dst_network_ids = Column(column_type=list, default=list)
#     unreachable_network_pairs = Column(column_type=list, default=list)

#     @property
#     def key(self):
#         """
#         Key these by testid, category id and network IP
#         """
#         return '_'.join([self.testid, self.src_network_ip, self.category_id])


class BlockedIPData(drecord.MapRecord):
    """
    This records a set of IPs blocked from communication as per DFW rules.
    """
    blocked_ips = Column(
        column_type=set, indexed=True, schema_name='blocked_ips_set')
    filter_name = Column(
        indexed=True, key_col=True, schema_name='filter_name_register')

    @property
    def key(self):
        """
        Key these by test id
        """
        return "%s_%s" % (self.filter_name, self.testid)


class TrafficConfig(drecord.MapRecord):
    """
    This record maintains the basic information on AddOn Traffic being run at
    different endpoints.
    """
    index = False

    vif_id = Column(schema_name='vif_id_register', key_col=True)

    # Stores JSON encoded information on servers to run on this
    # endpoint.
    servers = Column(column_type=str, schema_name='servers_register')
    # Stores JSON encoded information on destinations to which traffic
    # should be sent. Clients are identified by the destination IP,
    # protocol and port pair.
    clients = Column(column_type=str, schema_name='clients_register')

    @property
    def key(self):
        """
        Key these by test id and VIF id combination.
        """
        return '%s_%s' % (self.testid, self.vif_id)


class Endpoint(drecord.MapRecord):
    """
    This saves the endpoint ip address and hypervisor mapping details
    """
    mac_address = Column(
        indexed=False, schema_name='mac_address_register')
    ip_address = Column(
        indexed=True, schema_name='ip_address_register', key_col=True)
    prefix = Column(
        indexed=False, column_type=int, schema_name='prefix_register')
    iface = Column(
        indexed=False, schema_name='iface_register')
    hv_type = Column(
        indexed=True, schema_name='hv_type_register', default='')
    hv_ip = Column(
        indexed=True, schema_name='hv_ip_register', default='')
    test_management_ip = Column(
        indexed=True, schema_name='test_management_ip_register')
    created = Column(column_type=bool, indexed=False, default=False,
                     schema_name='created_flag')

    @property
    def key(self):
        return '%s_%s' % (self.testid, self.ip_address)


class IPRecord(drecord.SearchRecord):
    """
    This contains stock data on all the different types of supported traffic
    above IPv4 (so UDP, TCP, ICMP)
    """
    created = Column(
        'created',
        column_type=float,
        indexed=True,
        stored=True,
        default=time.time)
    src = Column(indexed=True)
    dst = Column(indexed=True)
    latency = Column(column_type=float, default=0.0)

    # these should be overriden if you want any traffic to pass
    failed = True
    connected = False
    protocol = 'IP'

    @property
    def create_request(self):
        create_req = super(IPRecord, self).create_request
        ret_val = [create_req]
        counter_type = 'failed' if self.failed else 'success'
        if self.connected:
            counter_type += '_connected'
        else:
            counter_type += '_disconnected'
        req_cnt = RequestCounts(**{
            counter_type: 1,
            'created': int(self.created)
        })
        update_rc_req = req_cnt.map_create_request
        update_rc_req.key = '%s_%d' % (self.testid, int(self.created))
        ret_val.append(update_rc_req)
        if self.failed:
            fault_req = Fault(
                src=self.src,
                dst=self.dst,
                created=self.created,
                connected=self.connected,
                protocol=self.protocol).create_request
            ret_val.append(fault_req)
        return ret_val


class ICMPRecord(IPRecord):
    """
    This describes the data that we save from icmp requests
    """
    ICMP_ECHOREPLY = 0
    protocol = 'ICMP'

    expected_icmp = Column(column_type=int, indexed=True)
    icmp_type = Column(column_type=int, indexed=True)
    attempts = Column(column_type=int)

    @property
    def failed(self):
        """
        A failure is mismatched icmp reply codes
        """
        return self.expected_icmp != self.icmp_type

    @property
    def connected(self):
        """
        If the expected reply code is ECHOREPLY then these two endpoints
        are connected
        """
        return self.expected_icmp == self.ICMP_ECHOREPLY


class ARPRecord(IPRecord):
    """
    This describes the data that we save from arp requests. This is a little
    not ok since this is below IP.
    """
    protocol = 'ARP'

    connected = Column(column_type=bool, indexed=True)
    dst_mac = Column(indexed=True)
    src_mac = Column(indexed=True)
    attempts = Column(column_type=int)

    @property
    def failed(self):
        """
        A failure is an empty destination mac if we are connected or
        a populated destination mac if we are not connected
        """
        return (not bool(self.dst_mac) and self.connected
                ) or (bool(self.dst_mac) and not self.connected)


class TransportRecord(IPRecord):
    """
    Base class for tcp and udp records. For now these records
    are pretty simple.  This can also be a base class for other
    protocols as they are needed
    """
    connected = Column(column_type=bool, indexed=True)
    success = Column(column_type=bool, indexed=True)

    @property
    def failed(self):
        """
        A failure is not a success. Makes sense.
        """
        return not self.success


class TCPRecord(TransportRecord):
    """
    Nothing special for tcp
    """
    protocol = 'TCP'


class UDPRecord(TransportRecord):
    """
    Nothing special for udp
    """
    protocol = 'UDP'
