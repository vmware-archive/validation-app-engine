#!/bin/env/python
'''
This module implements the primary interface for Traffic Controller
system in scale framework. Any traffic controller in future, be it for
On prem, cloud or hybrid setup, it must adhere to this interface.
'''
import abc
import logging


class TrafficController(object):
    __metadata__ = abc.ABCMeta

    def __init__(self):
        self.log = logging.getLogger(__name__)

    @abc.abstractmethod
    def register_traffic(self, traffic_config):
        pass

    @abc.abstractmethod
    def unregister_traffic(self, traffic_config):
        pass

    @abc.abstractmethod
    def start_traffic(self):
        pass

    @abc.abstractmethod
    def stop_traffic(self):
        pass

    @abc.abstractmethod
    def restart_traffic(self):
        pass
