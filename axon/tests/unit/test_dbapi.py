#!/usr/bin/env python
# Copyright (c) 2019 VMware, Inc. All Rights Reserved.
# SPDX-License-Identifier: BSD-2 License
# The full license information can be found in LICENSE.txt
# in the root directory of this project.

"""
unittests for dbapi
"""
import pytest
import uuid

import axon.db.models.traffic_models as traffic_models
from axon.db.backends.riak.riak_dbapi import RiakDatabaseAPI


@pytest.fixture(scope="module")
def dbapi():
    # runner ip so we can see the requests in the nginx logs
    host = "10.172.51.192"
    port = 8098
    return RiakDatabaseAPI(host=host, port=port)


@pytest.fixture(scope="module")
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


@pytest.fixture(scope="module")
def requestcounts():
    init_data = {
        "success_disconnected": 1,
        "created": 1539199940.916991,
        "failed_disconnected": 2,
        "testid": "d2501224-e906-485a-8253-03dde469e516",
        "success_connected": 3,
        "failed_connected": 4
    }
    rec = traffic_models.RequestCounts(**init_data)
    rec.key = str(uuid.uuid4())
    return rec


class TestDBAPI(object):
    """
    TestDBAPI
    """

    def test_write(self, dbapi, tcprecord):
        """
        test_write
        """
        responses = dbapi.write(tcprecord)
        for response in responses:
            assert response.status_code == 204

    def test_read(self, dbapi, tcprecord):
        """
        test_read
        """
        response = dbapi.read(tcprecord)
        assert response.status_code == 200
        read_value = response.json()
        print(read_value)
        assert read_value == tcprecord._as_dict()

    def test_query(self, dbapi, tcprecord):
        """
        test_query
        """
        response = dbapi.query(
            model_cls=type(tcprecord),
            params={"testid": tcprecord.testid}
        )
        assert response.status_code == 200
        query_response = response.json()
        assert "response" in query_response
        query_response = query_response["response"]
        assert "docs" in query_response
        assert query_response["numFound"] > 0
        records = query_response["docs"]
        assert any([rec["testid"] == tcprecord.testid for rec in records])

    def test_delete(self, dbapi, tcprecord):
        """
        test_delete
        """
        response = dbapi.delete(tcprecord)
        assert response.status_code == 204
