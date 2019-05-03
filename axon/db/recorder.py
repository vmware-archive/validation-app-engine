#!/usr/bin/env python
# Copyright (c) 2019 VMware, Inc. All Rights Reserved.
# SPDX-License-Identifier: BSD-2 License
# The full license information can be found in LICENSE.txt
# in the root directory of this project.

import logging
from multiprocessing import Queue

from axon.db.sql.analytics import session_scope
from axon.db.sql.repository import Repositories
from axon.db.wavefront.wavefront_client import WavefrontClient
from axon.db.record_count import SqlRecordCountHandler, \
    WavefrontRecordCountHandler


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


class SqlDbRecorder(TrafficRecorder):
    log = logging.getLogger(__name__)

    def __init__(self):
        super(SqlDbRecorder, self).__init__()
        self._queue = Queue(1000)
        self._repositery = Repositories()
        SqlRecordCountHandler(self._queue).start()

    def record_traffic(self, record):
        self._queue.put(record)
        try:
            with session_scope() as _session:
                self._repositery.create_record(_session, **record.as_dict())
        except Exception as e:
            self.log.exception(
                "Exception %s happened during recording traffic" % e)


class WaveFrontRecorder(TrafficRecorder):
    log = logging.getLogger(__name__)

    def __init__(self, host, proxy=False, token=None):
        super(WaveFrontRecorder, self).__init__()
        self._queue = Queue(1000)
        self._wf_client = WavefrontClient(host, proxy, token)
        WavefrontRecordCountHandler(self._queue, self._wf_client).start()

    def record_traffic(self, record):
        self._queue.put(record)
        self._wf_client.create_traffic_record(record)
