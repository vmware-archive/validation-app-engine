#!/usr/bin/env python
# Copyright (c) 2020 VMware, Inc. All Rights Reserved.
# SPDX-License-Identifier: BSD-2 License
# The full license information can be found in LICENSE.txt
# in the root directory of this project.

import ipaddress
import logging
import platform

log = logging.getLogger(__name__)


def is_ipv6_address(address):
    try:
        if address == 'localhost':
            _address = '127.0.0.1'
        elif address == 'ip6-localhost':
            _address = '::1'
        else:
            _address = address
        return ipaddress.ip_address(_address).version == 6
    except Exception as err:
        log.exception(err)
        log.warn("Error while trying to interprete %s as ip address.",
                 address)
        return False


def is_py3():
    return platform.python_version().startswith('3')
