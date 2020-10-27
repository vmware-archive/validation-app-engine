#!/usr/bin/env python
# Copyright (c) 2019 VMware, Inc. All Rights Reserved.
# SPDX-License-Identifier: BSD-2 License
# The full license information can be found in LICENSE.txt
# in the root directory of this project.

from axon.utils.network_utils import NamespaceManager


class NamespaceApp(object):
    def __init__(self):
        self._ns_manager = NamespaceManager()

    def list_namespaces(self):
        return self._ns_manager.get_all_namespaces()

    def get_namespace(self, namespace):
        return self._ns_manager.get_namespace(namespace)

    def list_namespaces_ips(self):
        return self._ns_manager.get_all_namespaces_ips()
