#!/usr/bin/env python
# Copyright (c) 2019 VMware, Inc. All Rights Reserved.
# SPDX-License-Identifier: BSD-2 License
# The full license information can be found in LICENSE.txt
# in the root directory of this project.

"""
Riak API Client
"""
import logging
import requests
# python 2 and 3 compatibility
import six.moves.urllib as urllib

# seconds
API_TIMEOUT = 5
RETRY_WAIT = 10
NUM_RETRIES = 3


class Client(object):
    """
    A simple, requests-based HTTP API client, suitable for use by
    management and debugging utilities.
    """

    def __init__(self, host, port=None, user=None, password=None):
        self._session = None
        self.host = host
        self.port = port if port else 80
        self.user = user
        self.password = password
        # TODO get testid from config
        self.testid = None
        self.log = logging.getLogger(__name__)

    @property
    def session(self):
        if not self._session:
            self._init_session()
        return self._session

    @property
    def headers(self):
        return self.session.headers

    def _init_session(self):
        self._session = requests.Session()
        self._session.headers.update({"content-type": "application/json"})
        if self.user and self.password:
            self._session.auth = (self.user, self.password)

    def _write(self,
               request_dict,
               timeout=API_TIMEOUT,
               retry_after=RETRY_WAIT,
               num_retries=NUM_RETRIES):
        path = request_dict["path"]
        payload = request_dict["data"]
        url = "http://{}:{}{}".format(self.host, self.port, path)
        self.log.debug("POST request for url [%s] with data [%r]", url,
                       payload)
        # we don't retry post at the client level, since that can have
        # really bad application-level side effects if we write multiple times
        response = self.session.post(url=url, data=payload, timeout=timeout)
        # self.log.debug("response status [%d]", response.status_code)
        return response

    def _read(self,
              request_dict,
              timeout=API_TIMEOUT,
              retry_after=RETRY_WAIT,
              num_retries=NUM_RETRIES):
        path = request_dict["path"]
        # params = request_dict["params"]
        url = "http://{}:{}{}".format(self.host, self.port, path)
        self.log.debug("GET request for url [%s]", url)
        response = self.session.get(url, timeout=timeout)
        self.log.debug("response status [%d]", response.status_code)
        return response

    def _delete(self,
                request_dict,
                timeout=API_TIMEOUT,
                retry_after=RETRY_WAIT,
                num_retries=NUM_RETRIES):
        path = request_dict["path"]
        # params = request_dict["params"]
        url = "http://{}:{}{}".format(self.host, self.port, path)
        self.log.debug("DELETE request for url [%s]", url)
        response = self.session.delete(url, timeout=timeout)
        self.log.debug("response status [%d]", response.status_code)
        return response


class RiakClient(Client):
    def __init__(self, host, port, user=None, password=None):
        super(RiakClient, self).__init__(host, port, user, password)

    def _handle_response(self, response):
        """
        response parsing logic
        """
        return response

    # API

    def write(self, models):
        responses = []
        if not hasattr(models, "__iter__"):
            models = [models]
        for model in models:
            req = model.create_request
            # some models return multiple create_requests
            if hasattr(req, "__iter__"):
                for sub_request in req:
                    request_dict = sub_request._as_dict()
                    resp = self._write(request_dict)
                    hresp = self._handle_response(resp)
                    responses.append(hresp)
            else:
                request_dict = req._as_dict()
                resp = self._write(request_dict)
                hresp = self._handle_response(resp)
                responses.append(hresp)
        if len(responses) == 1:
            return responses[0]
        return responses

    def read(self, models):
        responses = []
        if not hasattr(models, "__iter__"):
            models = [models]
        for model in models:
            req = model.read_request
            request_dict = req._as_dict()
            resp = self._read(request_dict)
            hresp = self._handle_response(resp)
            responses.append(hresp)
        if len(responses) == 1:
            return responses[0]
        return responses

    def delete(self, models):
        responses = []
        if not hasattr(models, "__iter__"):
            models = [models]
        for model in models:
            req = model.delete_request
            request_dict = req._as_dict()
            resp = self._delete(request_dict)
            hresp = self._handle_response(resp)
            responses.append(hresp)
        if len(responses) == 1:
            return responses[0]
        return responses

    def query(self, model_cls, params):
        # build the query
        query_url = "/search/query/{}?".format(model_cls.bucketname)
        q_params_string = ""
        for field_name, field_value in params.items():
            # TODO support conditional filters
            q_params_string += str(field_name)
            q_params_string += ":"
            q_params_string += field_value
        query_dict = {"q": q_params_string,
                      "wt": "json",
                      "rows": 100}
        query_url += urllib.parse.urlencode(query_dict)
        print(query_url)
        self.log.info(query_url)
        # make the api call
        request_dict = {"path": query_url}
        response = self._read(request_dict)
        return response
