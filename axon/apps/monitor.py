#!/usr/bin/env python
# Copyright (c) 2020 VMware, Inc. All Rights Reserved.
# SPDX-License-Identifier: BSD-2 License
# The full license information can be found in LICENSE.txt
# in the root directory of this project.
"""
App for Resource Monitoring.
Collects System CPU/Memory as well as AXON CPU/ Memory.
"""
import logging
import os
import psutil
import queue
import threading
import time

from multiprocessing import Queue

from axon.apps.base import BaseApp
from axon.db.record import ResourceRecord


log = logging.getLogger(__name__)

class ResourceMonitor(BaseApp):
    def __init__(self, rqueue, interval=3, proc_name='runner'):
        """
        A simple resource monitor that writes cpu / memory percentage
        to wavefront at requested interval.
        """
        self._rqueue = rqueue    # records queue to put records onto.
        self._interval = interval
        self._switch = threading.Event()
        self._proc_name = proc_name

    def run(self):
        while self._switch.is_set():
            t = int(time.time())

            sys_cpu_percent = psutil.cpu_percent()
            sys_mem_percent = psutil.virtual_memory().percent

            p = psutil.Process(os.getpid())
            axon_cpu_percent = p.cpu_percent()
            axon_mem_percent = p.memory_percent()

            rec = ResourceRecord(sys_cpu_percent, sys_mem_percent,
                                 axon_cpu_percent, axon_mem_percent)
            try:
                self._rqueue.put(rec, block=False, timeout=2)
            except queue.Full:
                log.error("Cann't put Resource record %r into the queue.",
                          rec)

            time.sleep(self._interval)

    def stop(self):
        self._switch.clear()

    def start(self):
        """
        Starts Resource monitoring (in a separate thread)
        """
        self._switch.set()
        self._thread = threading.Thread(target=self.run)
        self._thread.setDaemon(True)
        self._thread.start()


if __name__ == '__main__':
    q = queue.Queue()   # Queue()
    monitor = ResourceMonitor(rqueue=q)
    monitor.start()

    time.sleep(10)

    while True:
        try:
            rec = q.get(block=False)
            print (rec)
        except queue.Empty:
            break
