#!/usr/bin/env python
# Copyright (c) 2019 VMware, Inc. All Rights Reserved.
# SPDX-License-Identifier: BSD-2 License
# The full license information can be found in LICENSE.txt
# in the root directory of this project.

import os
import platform
import socket

from axon.common import utils

LINUX_OS = "Linux" in platform.uname()
utils.setup_logging()


# Traffic Server Configs
REQUEST_QUEUE_SIZE = 100
PACKET_SIZE = 1024
ALLOW_REUSE_ADDRESS = True


# Env Configs
TEST_ID = os.environ.get('TEST_ID', None)
TESTBED_NAME = os.environ.get('TESTBED_NAME', None)


# Wavefront recorder configs
WAVEFRONT_PROXY_ADDRESS = os.environ.get('WAVEFRONT_PROXY_ADDRESS', None)
WAVEFRONT_SERVER_ADDRESS = os.environ.get('WAVEFRONT_SERVER_ADDRESS', None)
WAVEFRONT_SERVER_API_TOKEN = os.environ.get('WAVEFRONT_SERVER_API_TOKEN', None)
WAVEFRONT_SOURCE_TAG = os.environ.get('WAVEFRONT_SOURCE', socket.gethostname())
WAVEFRONT_REPORT_PERC = float(os.environ.get('WAVEFRONT_REPORT_PERC', 1.0))


# Namespace Configs
NAMESPACE_MODE = os.environ.get("NAMESPACE_MODE", False)
NAMESPACE_MODE = True if NAMESPACE_MODE in ['True', True] else False
NAMESPACE_INTERFACE_NAME_PREFIXES = ["veth", "eth"]


# Recorder Configs
RECORDER = os.environ.get('RECORDER', None)
RECORD_COUNT_UPDATER_SLEEP_INTERVAL = 30
RECORD_UPDATER_THREAD_POOL_SIZE = 50
