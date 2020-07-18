#!/usr/bin/env python
# Copyright (c) 2019 VMware, Inc. All Rights Reserved.
# SPDX-License-Identifier: BSD-2 License
# The full license information can be found in LICENSE.txt
# in the root directory of this project.

from axon.utils.network_utils import InterfaceManager


class InterfaceApp(object):
    def __init__(self):
        self._if_mngr = InterfaceManager()

    def list_interfaces(self):
        return self._if_mngr.get_all_interfaces()

    def get_interface(self, name):
        return self._if_mngr.get_interface(name)
