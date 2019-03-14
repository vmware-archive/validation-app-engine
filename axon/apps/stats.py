#!/usr/bin/env python
# Copyright (c) 2019 VMware, Inc. All Rights Reserved.
# SPDX-License-Identifier: BSD-2 License
# The full license information can be found in LICENSE.txt
# in the root directory of this project.

import time

from axon.db.local import session_scope
from axon.db.local.repository import Repositories


class StatsApp(object):
    def __init__(self):
        self._repository = Repositories()

    def get_failure_count(self, start_time=None, end_time=None,
                          destination=None, port=None):
        if not start_time:
            start_time = time.time() - 300
        filters = {'success': False}
        if port:
            filters['port'] = port
        if destination:
            filters['dst'] = destination
        if not end_time:
            end_time = time.time()
        with session_scope() as session:
            return self._repository.record.get_record_count(
                session, start_time, end_time, **filters)

    def get_success_count(self, start_time=None, end_time=None,
                          destination=None, port=None):
        if not start_time:
            start_time = time.time() - 300
        filters = {'success': True}
        if port:
            filters['port'] = port
        if destination:
            filters['dst'] = destination
        if not end_time:
            end_time = time.time()
        with session_scope() as session:
            return self._repository.record.get_record_count(
                session, start_time, end_time, **filters)

    def get_failures(self, start_time=None, end_time=None,
                     destination=None, port=None):
        if not start_time:
            start_time = time.time() - 300
        if not end_time:
            end_time = time.time()
        filters = {'success': False}
        if port:
            filters['port'] = port
        if destination:
            filters['dst'] = destination
        with session_scope() as session:
            return self._repository.record.get_records(
                session, start_time, end_time, **filters)
