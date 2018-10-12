from axon.traffic.connected_state import ConnectedState
from axon.traffic.manager import RootNsServerManager, NamespaceServerManager,\
    NamespaceClientManager, RootNsClientManager
from axon.utils.network_utils import NamespaceManager, Namespace,\
    InterfaceManager


PRIMARY_IFACE_NAME = "nsx-eth0"


class AxonRootNamespaceServerAgent(object):
    """
    Launch Servers in Root Namespace
    """
    def __init__(self):
        self.mngrs_map = {}
        self.connected_state = ConnectedState()
        self.primary_if = InterfaceManager().get_interface(PRIMARY_IFACE_NAME)

    def start_servers(self, namespace='root'):
        """
        Start Set of default servers
        :return: None
        """
        mngr = RootNsServerManager() if not \
            self.mngrs_map.get(namespace) else self.mngrs_map.get(namespace)
        servers = self.connected_state.get_servers(self.primary_if['address'])
        servers = servers if servers else []
        for proto, port in servers:
            mngr.start_server(proto, port, self.primary_if['address'])
        self.mngrs_map[namespace] = mngr

    def stop_servers(self, namespace='root'):
        """
        Stop all Servers
        :return: None
        """
        for mngr in self.mngrs_map.values():
            mngr.stop_all_servers()

    def add_server(self, port, protocol, namespace='root'):
        """
        Run a Server in a root namespace
        :param port: port on which server will listen
        :type port: int
        :param protocol: protocol on which server will listen
        :type protocol: str
        :return: None
        """
        mngr = RootNsServerManager() if not \
            self.mngrs_map.get(namespace) else self.mngrs_map.get(namespace)
        mngr.start_server(protocol, port, self.primary_if['address'])
        self.connected_state.update_servers(
            self.primary_if["address"], [(protocol, port)])
        self.mngrs_map[namespace] = mngr

    def list_servers(self):
        server_list = []
        for mngr in self.mngrs_map.values():
            server_list.extend(mngr.list_servers())
        return server_list

    def get_server(self, protocol, port):
        server_list = []
        for mngr in self.mngrs_map.values():
            server_list.extend(mngr.get_server(protocol, port))
        return server_list

    def stop_server(self, protocol, port, namespace='root'):
        for mngr in self.mngrs_map.values():
            mngr.stop_server(port, protocol)


class AxonNameSpaceServerAgent(AxonRootNamespaceServerAgent):
    """
    Launch Servers in different namespaces
    """

    def __init__(self, ns_list=None, ns_interface_map=None):
        super(AxonNameSpaceServerAgent, self).__init__()
        self._ns_list = ns_list
        self._ns_iterface_map = ns_interface_map
        self._setup()

    def _setup(self):
        if not self._ns_list or not self._ns_iterface_map:
            mngr = NamespaceManager()
            self._ns_list = mngr.get_all_namespaces()
            self._ns_iterface_map = mngr.get_namespace_interface_map()

    def start_servers(self, namespace=None):
        """
        Start a set of default server in given namespace
        :param namespace: namespace name
        :type namespace: str
        :return: None
        """
        ns_list = [namespace] if namespace else self._ns_list
        for ns in ns_list:
            interface = self._ns_iterface_map.get(ns)
            servers = self.connected_state.get_servers(interface)
            if interface is None or not servers:
                continue
            ns_mngr = NamespaceServerManager(ns)
            for proto, port in servers:
                ns_mngr.start_server(proto, port, interface)
            self.mngrs_map[ns] = ns_mngr

    def stop_servers(self, namespace=None):
        """
        Stop all server in given namespace
        :return: None
        """
        ns_list = [namespace] if namespace else self._ns_list
        for ns, mngr in self.mngrs_map.items():
            if ns in ns_list:
                mngr.stop_all_servers()

    def add_server(self, port, protocol, namespace=None):
        """
        Run a Server in a given namespace
        :param port: port on which server will listen
        :type port: int
        :param protocol: protocol on which server will listen
        :type protocol: str
        :param namespace: namespace name
        :type namespace: str
        :return: None
        """
        ns_list = [namespace] if namespace else self._ns_list
        for ns in ns_list:
            ns_mngr = NamespaceServerManager(ns) if not \
                self.mngrs_map.get(ns) else self.mngrs_map.get(ns)
            interface = Namespace(ns).interfaces[0].address
            ns_mngr.start_server(protocol, port, interface)
            self.connected_state.update_servers(
                interface, [(protocol, port)])
            self.mngrs_map[ns] = ns_mngr

    def stop_server(self, protocol, port, namespace=None):
        ns_list = [namespace] if namespace else self._ns_list
        for ns in ns_list:
            server_mngr = self.mngrs_map.get(ns)
            if server_mngr:
                server_mngr.stop_server(port, protocol, ns)


class AxonRootNamespaceClientAgent(object):
    """
    Launch Servers in Root Namespace
    """
    def __init__(self):
        self.mngrs_map = {}
        self.connected_state = ConnectedState()
        self.primary_if = InterfaceManager().get_interface(PRIMARY_IFACE_NAME)

    def start_clients(self):
        clients = self.connected_state.get_clients(self.primary_if['address'])
        clients = clients if clients else []
        if clients:
            mngr = RootNsClientManager(clients)
            mngr.start_client(self.primary_if['address'])
            self.mngrs_map['root'] = mngr

    def stop_clients(self, namespace='root'):
        """
        Stop all Clients
        :return: None
        """
        for mngr in self.mngrs_map.values():
            mngr.stop_clients()

    def stop_client(self, src):
        for mngr in self.mngrs_map.values():
            mngr.stop_client(src)


class AxonNameSpaceClientAgent(AxonRootNamespaceClientAgent):
    """
    Launch Servers in different namespaces
    """

    def __init__(self, ns_list=None, ns_iterface_map=None):
        super(AxonNameSpaceClientAgent, self).__init__()
        self._ns_list = ns_list
        self._ns_iterface_map = ns_iterface_map
        self._setup()

    def _setup(self):
        if not self._ns_list or not self._ns_iterface_map:
            mngr = NamespaceManager()
            self._ns_list = mngr.get_all_namespaces()
            self._ns_iterface_map = mngr.get_namespace_interface_map()

    def start_clients(self, namespace=None):
        ns_list = [namespace] if namespace else self._ns_list
        for ns in ns_list:
            interface = self._ns_iterface_map.get(ns)
            if not interface:
                continue
            clients = self.connected_state.get_clients(interface[0].address)
            if not clients:
                continue
            ns_mngr = NamespaceClientManager(ns, clients)
            src = Namespace(ns).interfaces[0].address
            ns_mngr.start_client(src)
            self.mngrs_map[ns] = ns_mngr

    def stop_clients(self, namespace=None):
        ns_list = [namespace] if namespace else self._ns_list
        for ns, mngr in self.mngrs_map.items():
            if ns in ns_list:
                mngr.stop_clients()

    def stop_client(self, src):
        for namespace, interface in self._ns_iterface_map.items():
            if interface is None or interface != src:
                continue
            ns_mngr = self.mngrs_map.get(namespace)
            if ns_mngr:
                ns_mngr.stop_client(src)
