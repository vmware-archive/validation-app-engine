#!/usr/bin/env python
# Copyright (c) 2019 VMware, Inc. All Rights Reserved.
# SPDX-License-Identifier: BSD-2 License
# The full license information can be found in LICENSE.txt
# in the root directory of this project.

import logging
import threading
import time

from axon.db.sql.analytics import session_scope
from axon.db.sql.repository import Repositories


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
        self._repositery = Repositories()
        self._lock = threading.Lock()
        self._success_count = 0
        self._failure_count = 0
        self._latency_sum = 0
        self._samples = 0
        update_thread = threading.Thread(target=self._update_counters)
        update_thread.daemon = True
        update_thread.start()

    def _create_record_count(self, success_count, failure_count, created):
        try:
            with session_scope() as _session:
                self._repositery.create_record_count(
                    _session, self._success_count,
                    self._failure_count, created)
        except Exception as e:
            self.log.exception(e)

    def _create_latency_stats(self, latency_sum, samples, created):
        try:
            with session_scope() as _session:
                self._repositery.create_latency_stats(
                    _session, self._latency_sum,
                    self._samples, created)
        except Exception as e:
            self.log.exception(e)

    def _update_counters(self):
        self.log.info("Starting RequestCount/Latency Update Thread")
        while True:
            time.sleep(60)
            with self._lock:
                created_time = int(time.time())
                if self._success_count > 0 or self._failure_count > 0:
                    self._create_record_count(
                        self._success_count, self._failure_count, created_time)
                if self._samples > 0:
                    self._create_latency_stats(
                        self._latency_sum, self._samples, created_time)
                self._success_count = 0
                self._failure_count = 0
                self._latency_sum = 0
                self._samples = 0

    def record_traffic(self, record):
        with self._lock:
            if record.success:
                self._success_count += 1
                self._latency_sum += record.latency
                self._samples += 1
            else:
                self._failure_count += 1
        with session_scope() as _session:
            self._repositery.create_record(_session, **record.as_dict())
