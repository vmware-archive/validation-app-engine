import abc
from collections import defaultdict
import six
import platform
if "Linux" in platform.uname():  # noqa
    from nsenter import Namespace

from axon.traffic.servers import create_server_class
from axon.traffic.workers import WorkerProcess
from axon.traffic.clients import TrafficClient


class ServerRegistry(object):
    """
    Registry to holds all of the servers running across various namespaces
    """
    def __init__(self):
        self.__registry = defaultdict(dict)

    def add_server(self, namespace, port, protocol, server_obj):
        """
        Add server to registry
        :param namespace: name space where the server is running
        :type namespace: str
        :param port: port on which server is listening
        :type port: number
        :param protocol: protocol on which server is working
        :type protocol: str
        :param server_obj: server_obj, i.e. the server container object
        :type server_obj: ServerContainer
        :return: None
        """
        self.__registry[namespace][(port, protocol)] = server_obj

    def remove_server(self, namespace, port, protocol):
        """
        Remove server from registry
        :param namespace: name space where the server is running
        :type namespace: str
        :param port: port on which server is listening
        :type port: number
        :param protocol: protocol on which server is working
        :type protocol: str
        :return: None
        """
        if self.__registry[namespace].get((port, protocol)):
            del self.__registry[namespace][(port, protocol)]

    def get_server(self, namespace, port, protocol):
        """
        Get server from registry
        :param namespace: name space where the server is running
        :type namespace: str
        :param port: port on which server is listening
        :type port: number
        :param protocol: protocol on which server is working
        :type protocol: str
        :return: Server Object
        """
        return self.__registry[namespace].get((port, protocol))

    def get_all_servers(self):
        """
        Get all server objects
        """
        return self.__registry.items()


class ClientRegistry(object):
    """
    Registry to holds all of the clients running across various namespaces
    """
    def __init__(self):
        self.__registry = {}

    def add_client(self, namespace, client_obj):
        """
        Add client to registry
        :param namespace: name space where the client is running
        :type namespace: str
        :param client_obj: client container
        """
        self.__registry[namespace] = client_obj

    def remove_client(self, namespace):
        """
        Add client to registry
        :param namespace: name space where the client is running
        :type namespace: str
        """
        del self.__registry[namespace]

    def get_client(self, namespace):
        """
        Get A client object from registry
        :param namespace: namespace in which client is running
        :type namespace: str
        :param src: src ip on which client is bound to
        :type src: str
        :return: Client object
        :rtype: TrafficClient
        """
        return self.__registry[namespace]

    def get_all_client(self):
        """
        Get all client objects
        """
        return self.__registry.items()


@six.add_metaclass(abc.ABCMeta)
class ServerManager(object):
    """
    A class to manage servers
    """

    @abc.abstractmethod
    def start_server(self, *args, **kwargs):
        pass

    @abc.abstractmethod
    def stop_server(self, *args, **kwargs):
        pass

    @abc.abstractmethod
    def stop_all_servers(self, *args, **kwargs):
        pass

    @abc.abstractmethod
    def list_servers(self):
        pass

    @abc.abstractmethod
    def get_server(self, *args, **kwargs):
        pass


class RootNsServerManager(ServerManager):
    """
    Class which manages the servers in root NameSpace
    """

    ROOT_NAMESPACE_NAME = 'localhost'

    def __init__(self):
        self._server_registry = ServerRegistry()

    def start_server(self, protocol, port, src="0.0.0.0"):
        server_cls, args, kwargs = create_server_class(protocol, port, src)
        process = WorkerProcess(server_cls, args, kwargs)
        process.start()
        self._server_registry.add_server(
            self.ROOT_NAMESPACE_NAME, port, protocol, process)

    def stop_server(self, port, protocol):
        server_process = self._server_registry.get_server(
            self.ROOT_NAMESPACE_NAME, port, protocol)
        if server_process:
            server_process.stop()
            self._server_registry.remove_server(
                self.ROOT_NAMESPACE_NAME, port, protocol)

    def stop_all_servers(self):
        servers = [server for ns, conf_server_map in
                   self._server_registry.get_all_servers() for
                   conf, server in conf_server_map.items()]
        for server in servers:
            server.stop()

    def list_servers(self):
        servers = [(ns, conf) for ns, conf_server_map in
                   self._server_registry.get_all_servers() for
                   conf, server in conf_server_map.items()]
        return servers

    def get_server(self, protocol, port, namespace=None):
        servers = [(ns, conf) for ns, conf_server_map in
                   self._server_registry.get_all_servers() for
                   conf, server in conf_server_map.items() if
                   conf[0] == port and conf[1] == protocol]
        return servers


class NamespaceServerManager(RootNsServerManager):
    """
    Class which manages servers in a Given Namespace
    """

    NAMESPACE_PATH = '/var/run/netns/'

    def __init__(self, namespace):
        super(NamespaceServerManager, self).__init__()
        self._ns = namespace
        self._ns_full_path = self.NAMESPACE_PATH + self._ns

    def start_server(self, protocol, port, src="0.0.0.0"):
        server_cls, args, kwargs = create_server_class(protocol, port, src)
        process = WorkerProcess(server_cls, args, kwargs)
        with Namespace(self._ns_full_path, 'net'):
            process.start()
        self._server_registry.add_server(
            self._ns, port, protocol, process)

    def stop_server(self, port, protocol, namespace):
        server_process = self._server_registry.get_server(
            namespace, port, protocol)
        if server_process:
            with Namespace(self._ns_full_path, 'net'):
                server_process.stop()


@six.add_metaclass(abc.ABCMeta)
class ClientManager(object):
    """
    Class to manage Clients
    """

    @abc.abstractmethod
    def start_client(self, *args, **kwargs):
        """
        Start a Client
        """
        pass

    @abc.abstractmethod
    def stop_client(self, *args, **kwargs):
        """
        Stop a client
        """
        pass

    @abc.abstractmethod
    def stop_clients(self, *args, **kwargs):
        """
        Stop all Clients
        """
        pass


class RootNsClientManager(ClientManager):
    """
    Class which manages the clients in root NameSpace
    """

    ROOT_NAMESPACE_NAME = 'localhost'

    def __init__(self, clients):
        self._client_registry = ClientRegistry()
        self._clients = clients

    def start_client(self, src):
        process = WorkerProcess(TrafficClient, (src, self._clients), {})
        process.start()
        self._client_registry.add_client(self.ROOT_NAMESPACE_NAME, process)

    def stop_client(self, src):
        client = self._client_registry.get_client(self.ROOT_NAMESPACE_NAME)
        if client:
            client.stop()
            self._client_registry.remove_client(self.ROOT_NAMESPACE_NAME)

    def stop_clients(self):
        client = [client for namespace, client in
                  self._client_registry.get_all_client()]
        for client in client:
            client.stop()


class NamespaceClientManager(RootNsClientManager):
    """
    Class which manages Clients in a Given Namespace
    """

    NAMESPACE_PATH = '/var/run/netns/'

    def __init__(self, namespace, clients):
        super(NamespaceClientManager, self).__init__(clients)
        self._ns = namespace
        self._ns_full_path = self.NAMESPACE_PATH + self._ns

    def start_client(self, src):
        process = WorkerProcess(TrafficClient, (src, self._clients), {})
        with Namespace(self._ns_full_path, 'net'):
            process.start()
        self._client_registry.add_client(self.ROOT_NAMESPACE_NAME, process)

    def stop_client(self, src):
        client = self._client_registry.get_client(self.ROOT_NAMESPACE_NAME)
        if client:
            with Namespace(self._ns_full_path, 'net'):
                client.stop()
