#!/usr/bin/env python
# Copyright (c) 2019 VMware, Inc. All Rights Reserved.
# SPDX-License-Identifier: BSD-2 License
# The full license information can be found in LICENSE.txt
# in the root directory of this project.

import mock
import uuid

import axon.db.models.traffic_models as traffic_models
from axon.db.backends.riak.riak_dbapi import RiakDatabaseAPI
from axon.db.backends.riak.riak_client import \
    RiakClient
from axon.tests import base as test_base


def tcprecord():
    tcp_request_data = {
        "src": "30.0.1.2",
        "success": True,
        "latency": 0.0,
        "dst": "30.0.3.4",
        "created": 1539199940.916991,
        "connected": True,
        "testid": "d2501224-e906-485a-8253-03dde469e516"
    }
    rec = traffic_models.TCPRecord(**tcp_request_data)
    rec.key = str(uuid.uuid4())
    return rec


class TestRiakDatabaseAPI(test_base.BaseTestCase):
    """
    Test for RiakDatabaseAPI utilities
    """

    def setUp(self):
        super(TestRiakDatabaseAPI, self).setUp()
        host = "1.2.3.4"
        port = 8098
        self.db_api = RiakDatabaseAPI(host=host, port=port)

    @mock.patch.object(RiakClient, 'write')
    def test_write(self, mock_write):
        models = 'fake-models'
        self.db_api.write(models)
        mock_write.assert_called_with(models)

    @mock.patch.object(RiakClient, 'read')
    def test_read(self, mock_read):
        models = 'fake-models'
        self.db_api.read(models)
        mock_read.assert_called_with(models)

    @mock.patch.object(RiakClient, 'delete')
    def test_delete(self, mock_delete):
        models = 'fake-models'
        self.db_api.delete(models)
        mock_delete.assert_called_with(models)

    @mock.patch.object(RiakClient, 'query')
    def test_query(self, mock_query):
        kwargs = {'model_cls': type(tcprecord),
                  'params': {"testid": tcprecord().testid}}
        self.db_api.query(**kwargs)
        mock_query.assert_called_with(type(tcprecord),
                                      {"testid": tcprecord().testid})
