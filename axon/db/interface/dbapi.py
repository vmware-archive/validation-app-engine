#!/usr/bin/env python
# Copyright (c) 2019 VMware, Inc. All Rights Reserved.
# SPDX-License-Identifier: BSD-2 License
# The full license information can be found in LICENSE.txt
# in the root directory of this project.

"""
The single entry point for users.
"""
from abc import ABCMeta, abstractproperty, abstractmethod
import importlib
import inspect
import pkgutil
import six

from axon.db.dataclass_factory import dataclass_factory


@six.add_metaclass(ABCMeta)
class DatabaseAPI(object):
    """
    The single point of entry for client applications. This object acts as a
    facade to the rest of the database api, and handles the details of loading
    the appropriate Backend objects, clients, etc. based on the given config.
    """

    def __init__(self):
        self._class_cache = {}
        self.base_packages = (
            'axon.db.models',)

    @abstractproperty
    def backend(self):
        """
        Backend name as a lowercase string.
        """
        pass

    @abstractmethod
    def write(self, models):
        pass

    @abstractmethod
    def read(self, models):
        pass

    @abstractmethod
    def delete(self, models):
        pass

    @abstractmethod
    def query(self, *args, **kwargs):
        pass

    @property
    def models(self):
        """
        Allows users to access model classes by doing dbapi.models.ModelName
        """
        if not self._class_cache:
            self._load_classes()
        # allows for clean lookup syntax
        ModelRegistry = dataclass_factory(
            'ModelRegistry', list(self._class_cache.keys()))
        return ModelRegistry(**self._class_cache)

    def _load_classes(self):
        """
        Loads all possible classes given by base packages and put them in
        class cache
        """
        stack = set(self.base_packages)
        while stack:
            base_pkg = stack.pop()
            try:
                base = importlib.import_module(base_pkg)
                # In case it is a package that has no package in it
                if not getattr(base, '__path__', None):
                    self.__load_classes(base)
                    continue

                for _, modname, ispkg in pkgutil.iter_modules(base.__path__):
                    new_pkg = '.'.join((base_pkg, modname))
                    if not ispkg:
                        self.__load_classes(importlib.import_module(new_pkg))

                    else:
                        stack.add(new_pkg)
            except ImportError:
                pass

    def __load_classes(self, pkg):
        """
        Loads classes defined in given package

        Parameters
        ----------
        pkg: module
            Module which contains classes
        """
        for name, obj in inspect.getmembers(pkg):
            if inspect.isclass(obj):
                if name not in self._class_cache:
                    self._class_cache[name] = obj


def create_dbapi(db_config):
    """
    Factory function for instantiating a specific DatabaseAPI based on the
    given config.
    """
    # discover backends with import_module and import_lib
    pass
