#!/usr/bin/env python
# Copyright (c) 2020 VMware, Inc. All Rights Reserved.
# SPDX-License-Identifier: BSD-2 License
# The full license information can be found in LICENSE.txt
# in the root directory of this project.

import logging
import os
from sql30 import db


from axon.apps.base import BaseApp

log = logging.getLogger(__name__)
configs = None


class Config(db.Model, BaseApp):
    NAME = "CONFIG"
    DB_NAME = 'config.db'
    TABLE = 'config'
    DB_SCHEMA = {
        'db_name': DB_NAME,
        'tables': [
            {
                'name': TABLE,
                'fields': {
                    'param': 'text',
                    'value': 'text',
                    },
                'primary_key': 'param'  # avoid duplicate entries.
            }]
        }
    VALIDATE_BEFORE_WRITE = True

    DEFAULT_CONFIG = '/etc/axon/axon.conf'

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
        Reads config from default config file for the service.

        We do not write these configs into the database yet as database
        configs are supposd to overwrite.
        """
        configs = []
        if os.path.exists(self.DEFAULT_CONFIG):
            with open(self.DEFAULT_CONFIG, 'r') as fp:
                configs = fp.readlines()

        for config in configs:
            config = config.strip()
            if config.startswith('#'):
                continue
            param, val = config.split('=')
            self._params[param] = val   # initialize values.

    def load_from_db(self):
        """
        Load config params from database file to local cache.
        """
        configs = self.read()
        for key, val in configs:
            self._params[key] = val

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
        if record:
            self.update(condition={'param':param}, value=val)
        else:
            self.write(param=param, value=val)


def _get_configs():
    global configs
    if not configs:
        configs = Config()

    return configs


def get_param(param):
    return _get_configs().get_param(param)


def set_param(param, val):
    return _get_configs().set_param(param, val)
