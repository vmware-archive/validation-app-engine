#!/usr/bin/env python
# Copyright (c) 2019 VMware, Inc. All Rights Reserved.
# SPDX-License-Identifier: BSD-2 License
# The full license information can be found in LICENSE.txt
# in the root directory of this project.

import platform

LINUX_OS = "Linux" in platform.uname()

# Logging Constants
LINUX_LOG_DIR = "/var/log/axon"
WIN_LOG_DIR = "C:\\axon\\log"
LOG_DIR = LINUX_LOG_DIR if LINUX_OS else WIN_LOG_DIR
LOG_FILE = "axon.log"

# Axon Service Constants
AXON_PORT = 5678

# Recorder Constants
WAVEFRONT = 'wavefront'
