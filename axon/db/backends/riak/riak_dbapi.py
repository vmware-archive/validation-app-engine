#!/usr/bin/env python
# Copyright (c) 2019 VMware, Inc. All Rights Reserved.
# SPDX-License-Identifier: BSD-2 License
# The full license information can be found in LICENSE.txt
# in the root directory of this project.

"""
Riak DatabaseAPI
"""
import logging

from axon.db.interface.dbapi import DatabaseAPI
from axon.db.backends.riak.riak_client import \
    RiakClient


class RiakDatabaseAPI(DatabaseAPI):
    """
    RiakDatabaseAPI
    """

    def __init__(self, host="127.0.0.1", port=8098):
        super(RiakDatabaseAPI, self).__init__()
        self.log = logging.getLogger(__name__)
        self._client = None
        # default to localhost:8098
        self.host = host
        self.port = port

    @property
    def client(self):
        if not self._client:
            self._client = RiakClient(self.host, self.port)
        return self._client

    @property
    def backend(self):
        return "riak"

    def write(self, models):
        return self.client.write(models)

    def read(self, models):
        return self.client.read(models)

    def delete(self, models):
        return self.client.delete(models)

    def query(self, model_cls, params):
        """
        args should include the model cls or model class name
        kwargs should include field (db column name) as keys mapped to value
        or condition (lambda or function)
        """
        if isinstance(model_cls, str):
            model_cls = getattr(self.models, model_cls)
        return self.client.query(model_cls, params)
