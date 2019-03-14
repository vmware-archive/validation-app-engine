#!/usr/bin/env python
# Copyright (c) 2019 VMware, Inc. All Rights Reserved.
# SPDX-License-Identifier: BSD-2 License
# The full license information can be found in LICENSE.txt
# in the root directory of this project.

import logging

import rpyc
from rpyc.utils.server import ThreadPoolServer

from axon.apps.traffic import TrafficApp
from axon.apps.stats import StatsApp
from axon.apps.namespace import NamespaceApp
from axon.apps.interface import InterfaceApp
from axon.common import config as conf
from axon.db.local import init_session

rpyc.core.protocol.DEFAULT_CONFIG['allow_pickle'] = True


def exposify(cls):
    for key in dir(cls):
        val = getattr(cls, key)
        if callable(val) and not key.startswith("_"):
            setattr(cls, "exposed_%s" % (key,), val)
    return cls


@exposify
class exposed_Traffic(TrafficApp):
    pass


@exposify
class exposed_Stats(StatsApp):
    pass


@exposify
class exposed_Namespace(NamespaceApp):
    pass


@exposify
class exposed_Interface(InterfaceApp):
    pass


class AxonServiceBase(rpyc.Service):

    RPYC_PROTOCOL_CONFIG = rpyc.core.protocol.DEFAULT_CONFIG

    def __init__(self):
        super(AxonServiceBase, self).__init__()

    def on_connect(self, conn):
        print("Connected to %r", conn)

    def on_disconnect(self, conn):
        print("Disconnected from %r", conn)


class AxonService(AxonServiceBase):

    def __init__(self):
        super(AxonService, self).__init__()
        init_session()
        self.exposed_traffic = exposed_Traffic(conf)
        self.exposed_stats = exposed_Stats()
        self.exposed_namespace = exposed_Namespace()
        self.exposed_interface = exposed_Interface()


class AxonController(object):

    def __init__(self):
        self.axon_port = conf.AXON_PORT
        self.service = AxonService()
        self.protocol_config = self.service.RPYC_PROTOCOL_CONFIG
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.WARN)
        self.axon_service = ThreadPoolServer(
            self.service,
            port=self.axon_port,
            reuse_addr=True,
            protocol_config=self.protocol_config,
            logger=self.logger, nbThreads=50)

    def start(self):
        try:
            self.service.exposed_traffic.start_servers()
            self.service.exposed_traffic.start_clients()
        except Exception:
            self.logger.exception("Ooops!! Exception during Traffic Start")
        self.axon_service.start()

    def stop(self):
        try:
            self.service.exposed_traffic.stop_clients()
            self.service.exposed_traffic.stop_servers()
        except Exception:
            self.logger.exception("Ooops!! Exception during Traffic Stop")
        self.axon_service.close()


def main():
    axon_service = AxonController()
    axon_service.start()


if __name__ == '__main__':
    main()
