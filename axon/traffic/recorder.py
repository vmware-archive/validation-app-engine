#!/usr/bin/env python
# Copyright (c) 2019 VMware, Inc. All Rights Reserved.
# SPDX-License-Identifier: BSD-2 License
# The full license information can be found in LICENSE.txt
# in the root directory of this project.

import logging

from axon.db.local import session_scope
from axon.db.local.repository import Repositories
import axon.db.models.traffic_models as traffic_models
from axon.db.backends.riak.riak_dbapi import RiakDatabaseAPI


class TrafficRecorder(object):

    def record_traffic(self, record):
        raise NotImplementedError()


class StreamRecorder(TrafficRecorder):
    def record_traffic(self, record):
        print(
            "Traffic:%s Source:%s Destination:%s Latency:%s Success:%s"
            "Error:%s" % (record.traffic_type, record.src,
                          record.dst, record.latency,
                          record.success, record.error))


class LogFileRecorder(TrafficRecorder):
    def __init__(self, log_file):
        super(LogFileRecorder, self).__init__()
        self.log = self._get_logger(log_file)

    def _get_logger(self, log_file):
        log_formatter = logging.Formatter(
            '%(asctime)s::%(message)s')
        root_logger = logging.getLogger(__name__)
        root_logger.setLevel(logging.DEBUG)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(log_formatter)
        root_logger.addHandler(file_handler)
        return root_logger

    def record_traffic(self, record):
        self.log.info(
            "Traffic:%s Source:%s Destination:%s Latency:%s Success:%s "
            "Error:%s" % (record.traffic_type, record.src,
                          record.dst, record.latency,
                          record.success, record.error))


class SqliteDbRecorder(TrafficRecorder):
    def __init__(self):
        super(SqliteDbRecorder, self).__init__()
        self._repositery = Repositories()

    def record_traffic(self, record):
        with session_scope() as _session:
            self._repositery.create_record(_session, **record.as_dict())


# TODO add insert Batch insert to reduce database RTT
class RiakRecorder(TrafficRecorder):
    def __init__(self, host, port, test_id):
        self._test_id = test_id
        self._riak_api = RiakDatabaseAPI(host=host, port=port)

    def record_traffic(self, record):
        traffic_record = {
            "src": record.src,
            "dst": record.dst,
            "latency": record.latency,
            "success": record.success,
            "created": record.created,
            "testid": self._test_id,
            "connected": record.connected
        }
        if record.traffic_type == "TCP":
            rec = traffic_models.TCPRecord(**traffic_record)
        elif record.traffic_type == "UDP":
            rec = traffic_models.UDPRecord(**traffic_record)
        # Fire and forget
        self._riak_api.write(rec)
