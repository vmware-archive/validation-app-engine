#!/usr/bin/env python
# Copyright (c) 2019 VMware, Inc. All Rights Reserved.
# SPDX-License-Identifier: BSD-2 License
# The full license information can be found in LICENSE.txt
# in the root directory of this project.

import ast
import logging
import os
import platform

from axon.traffic.recorder import RiakRecorder

AXON_PORT = 5678
LINUX_OS = "Linux" in platform.uname()
LOG_DIR = "/var/log/axon" if LINUX_OS else "C:\\axon\\log"
LOG_FILE = "axon.log"
CLOUD_LINUX_INTERFACE = 'nsx-eth0'
CLOUD_WINDOWS_INTERFACE = 'Ethernet0'
NAMESPACE_INTERFACE_NAME_PREFIXES = ["veth", "eth"]


def create_log_dir():
    """
    Create Log directory
    """
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)


def setup_logging(log_dir, log_file='axon.log'):
    """
    Sets up Logging handlers and other environment.
    """
    log_file_name = os.path.join(log_dir, log_file)
    log_formatter = logging.Formatter(
        '%(asctime)s::%(levelname)s::%(threadName)s::'
        '%(module)s[%(lineno)04s]::%(message)s')
    root_logger = logging.getLogger()
    if root_logger.handlers:
        return
    root_logger.setLevel(logging.INFO)
    file_handler = logging.FileHandler(log_file_name)
    file_handler.setFormatter(log_formatter)
    root_logger.addHandler(file_handler)
    return root_logger


# setup logging
create_log_dir()
setup_logging(LOG_DIR)


# setup namespace and interface
NAMESPACE_MODE = ast.literal_eval(os.environ.get("NAMESPACE_MODE", 'False'))
PRIMARY_IFACE_NAME = CLOUD_LINUX_INTERFACE if LINUX_OS else \
    CLOUD_WINDOWS_INTERFACE

# setup database recorder
TEST_ID = os.environ.get("TEST_ID")
HELPER_IP = os.environ.get("HELPER_IP")
RIAK_PORT = os.environ.get("RIAK_PORT")

TRAFFIC_RECORDER = None
if HELPER_IP and TEST_ID and RIAK_PORT:
    TRAFFIC_RECORDER = RiakRecorder(HELPER_IP, RIAK_PORT, TEST_ID)
