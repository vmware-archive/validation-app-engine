#!/usr/bin/env python
# Copyright (c) 2019 VMware, Inc. All Rights Reserved.
# SPDX-License-Identifier: BSD-2 License
# The full license information can be found in LICENSE.txt
# in the root directory of this project.

import multiprocessing
import platform
if "Linux" in platform.uname():  # noqa
    from nsenter import Namespace as NsenterNamespace
import psutil
import subprocess
import axon.common.config as axon_config


def get_interfaces_in_namespace(return_dict):
    return_dict['result'] = psutil.net_if_addrs()
    return return_dict


class Namespace(object):
    """
    Namespace object which holds information name, id, interfaces inside
    """
    def __init__(self, name, id=None):
        self._name = name
        self._id = id
        self._interface_list = []
        self._discover_interfaces()

    @property
    def name(self):
        return self._name

    @property
    def id(self):
        return self._id

    @property
    def interfaces(self):
        return self._interface_list

    def as_dict(self):
        return dict(zip(['name', 'id', 'interfaces'],
                        [self.name, self.id, [interface.as_dict() for
                                              interface in self.interfaces]]))

    def _discover_interfaces(self):
        ns_path = '/var/run/netns/%s' % self.name
        manager = multiprocessing.Manager()
        return_dict = manager.dict()
        with NsenterNamespace(ns_path, 'net'):
            process = multiprocessing.Process(
                target=get_interfaces_in_namespace, args=(return_dict,))
            process.start()
            process.join()
        for name, snics in return_dict['result'].items():
            for nic in [snic for snic in snics if snic.family == 2]:
                self._interface_list.append(Interface(
                    name, nic.address, nic.family,
                    nic.netmask, nic.broadcast))


class NamespaceManager(object):
    """
    Class that controls all relevant NS on a machine
    - upon launch, discovers all namespaces
    - provide apis to get all the necessary information
    """

    def __init__(self):
        self._namespace_map = {}
        self._namespace_interface_map = {}
        self._linux_distro = "Linux" in platform.uname()
        self._discover_namespaces()

    def _discover_namespaces(self):
        if self._linux_distro:
            ns_list = subprocess.check_output(["ip", "netns", "list"])
            if not ns_list:
                return
            for ns in ns_list.rstrip().split("\n"):
                ns_info = ns.split()
                id = None
                if len(ns_info) > 1:
                    id = ns_info[1]
                name = ns_info[0]
                self._namespace_map[name] = Namespace(name, id)
                interfaces = Namespace(name, id).interfaces
                if interfaces:
                    self._namespace_interface_map[name] = \
                        Namespace(name, id).interfaces
                else:
                    self._namespace_interface_map[name] = None

    def get_namespace_interface_map(self):
        return self._namespace_interface_map

    def get_all_namespaces(self):
        """
        Get the list of all namespaces presnt in the system
        :return: List of namespace names
        :rtype: list
        """
        return self._namespace_map.keys()

    def get_namespace(self, namespace):
        ns = self._namespace_map.get(namespace)
        if ns:
            return ns.as_dict()
        else:
            return None

    def get_all_namespaces_ips(self):
        """
        Get the list of all namespaces ips address present in the system
        based on axon_config.NAMESPACE_INTERFACE_NAME_PREFIXES
        :return: List of namespace ips
        :rtype: list
        """
        namespaces_ips = []
        for np in self._namespace_map.values():
            interface = [iface for iface in np.interfaces for prefix in
                         axon_config.NAMESPACE_INTERFACE_NAME_PREFIXES
                         if prefix in iface.name]
            if not interface:
                continue
            namespaces_ips.append(interface[0].address)
        return namespaces_ips


class Interface(object):
    """
    Interface object which holds all the information related to interface
    """
    def __init__(self, name, address, family, netmask, broadcast):
        self._name = name
        self._address = address
        self._family = family
        self._netmask = netmask
        self._broadcast = broadcast

    @property
    def name(self):
        return self._name

    @property
    def address(self):
        return self._address

    @property
    def family(self):
        return self._family

    @property
    def netmask(self):
        return self._netmask

    @property
    def broadcast(self):
        return self._broadcast

    def as_dict(self):
        return dict(zip(['name', 'address', 'family', 'netmask', 'broadcast'],
                        [self.name, self.address, self.family, self.netmask,
                         self.broadcast]))


class InterfaceManager(object):
    """
    Class that controls all Interface information on host
    """
    def __init__(self):
        self._interface_map = {}
        self._discover_interfaces()

    def _discover_interfaces(self):
        addrs = psutil.net_if_addrs()
        for name, snics in addrs.items():
            for nic in [snic for snic in snics if snic.family == 2]:
                self._interface_map[name] = Interface(
                    name, nic.address, nic.family,
                    nic.netmask, nic.broadcast)

    def get_all_interfaces(self):
        """
        Get all the interface names present in the system
        :return:
        :rtype:
        """
        return self._interface_map.keys()

    def get_interface(self, name):
        """
        Get detail about a particular interface
        :param name: name of the interface
        :type name: str
        :return: interface object as dict
        :rtype: dict
        """
        interface = self._interface_map.get(name)
        if interface:
            return interface.as_dict()
        else:
            return None

    def get_interface_by_ip(self, ip):
        for name, interface in self._interface_map.items():
            if interface.address == ip:
                return name
