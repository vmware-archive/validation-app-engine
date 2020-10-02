#!/usr/bin/env python
# Copyright (c) 2020 VMware, Inc. All Rights Reserved.
# SPDX-License-Identifier: BSD-2 License
# The full license information can be found in LICENSE.txt
# in the root directory of this project.

import json
import logging
import os
import platform
import socket
import sys

from sql30 import db

from axon.apps.base import BaseApp
from axon.common import consts, utils

log = logging.getLogger(__name__)
configs = None


# # # # # All Configurable Variables set below # # # # #

LINUX_OS = "Linux" in platform.uname()
LOG_FILE = os.environ.get('LOG_FILE', consts.LOG_FILE)
LOG_DIR = os.environ.get('LOG_DIR', consts.LOG_DIR)
utils.setup_logging(log_dir=LOG_DIR, log_file=LOG_FILE)


# Traffic Server Configs
REQUEST_QUEUE_SIZE = 100
PACKET_SIZE = 1024
ALLOW_REUSE_ADDRESS = True


# Env Configs
TEST_ID = os.environ.get('TEST_ID', None)
TESTBED_NAME = os.environ.get('TESTBED_NAME', None)
AXON_PORT = int(os.environ.get('AXON_PORT', 5678))


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

ELASTIC_SEARCH_SERVER_ADDRESS = os.environ.get('ELASTIC_SEARCH_SERVER_ADDRESS', None)
ELASTIC_SEARCH_SERVER_PORT = os.environ.get(
    'ELASTIC_SEARCH_SERVER_PORT', consts.ELASTIC_SEARCH_PORT)

# # # # # End of Configurable Variables  # # # # #


class Config(db.Model, BaseApp):
    NAME = "CONFIG"
    DB_NAME = 'config.db'
    TABLE = 'config'
    SINGLE_QUOTE = '\''
    DOUBLE_QUOTE = '\"'

    DB_SCHEMA = {
        'db_name': DB_NAME,
        'tables': [
            {
                'name': TABLE,
                'fields': {
                    'param': 'text',
                    'value': 'text',
                    'typename': 'text',
                    },
                'primary_key': 'param'  # avoid duplicate entries.
            }]
        }
    VALIDATE_BEFORE_WRITE = True

    def __init__(self, db_file=None):
        # Set database name.
        db_name = db_file or self.DB_NAME
        super(Config, self).__init__(db_name=db_name)
        self.table = self.TABLE

        # set params
        self._params = {}

        # Read configs, load from db file.

        self._read_config()
        self.load_from_db()
        self.save_to_db()

    def _read_config(self):
        """
        Reads config from default config file.

        We do not write these configs into the database yet as database
        configs are supposed to overwrite.
        """

        module_name = sys.modules[__name__]
        VARS = [var for var in dir(module_name) if var.isupper()]
        for var in VARS:
            param, val = var, getattr(module_name, var)
            self._params[param] = val

    def _type_handler(self, val, type_name):

        types_map = {'str': lambda x: x,
                     'int': lambda x: int(x),
                     'float': lambda x: float(x),
                     'bool': lambda x: True if x == 'True' else False,
                     'list': lambda x: json.loads(x.replace(self.SINGLE_QUOTE,
                                                            self.DOUBLE_QUOTE)),
                     'dict': lambda x: json.loads(x.replace(self.SINGLE_QUOTE,
                                                            self.DOUBLE_QUOTE)),
                     'NoneType': lambda x: None,
                     }

        if type_name in types_map:
            return types_map[type_name](val)
        elif type_name == 'tuple':
            val = val.replace('(', '[').replace(')', ']')
            return tuple(types_map['list'](val))
        elif type_name == 'set':
            s_val = val.replace('{', '[').replace('}', ']')
            return set(types_map['list'](s_val))
        else:
            return val

    def load_from_db(self):
        """
        Load config params from database file to local cache.
        """
        configs = self.read()
        for key, val, type_name in configs:
            self._params[key] = self._type_handler(val, type_name)

    def save_to_db(self):
        """
        Save config params in local cache to database file.
        """
        for param, val in self._params.items():
            self._persist_param(param, val)

        self.commit()

    def get_param(self, param):
        """
        Return the value of a config param. Param is always
        returned from local cache as it is simply a reflector of database file.
        """
        return self._params.get(param, None)

    def set_param(self, param, val, write_to_db=True):
        self._params[param] = val

        if write_to_db:
            self._persist_param(param, val)
            self.commit()

    def _persist_param(self, param, val):
        """
        Sets a param, val in database file.
        """
        record = self.read(param=param)
        type_name = type(val).__name__
        if record:
            self.update(condition={'param': param}, value=str(val), typename=type_name)
        else:
            self.write(param=param, value=str(val), typename=type_name)


def _get_configs():
    global configs
    if not configs:
        configs = Config()

    return configs


def get_param(param):
    return _get_configs().get_param(param)


def set_param(param, val):
    return _get_configs().set_param(param, val)