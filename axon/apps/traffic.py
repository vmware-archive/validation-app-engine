import logging

from axon.traffic.connected_state import ConnectedState
from axon.traffic.agents import AxonRootNamespaceClientAgent,\
    AxonRootNamespaceServerAgent, AxonNameSpaceClientAgent,\
    AxonNameSpaceServerAgent
from axon.utils.network_utils import NamespaceManager


# Cloud has namespaces, but we dont want to run the server and agent inside the
# namespace since that namespace is created by product not user. User will run
# its app inside the root ns always.
# TODO(pksingh) Make it configurable for cloud workloads
NAMESPACE_MODE = False


class TrafficApp(object):

    def __init__(self):
        self.log = logging.getLogger(__name__)
        namespaces = NamespaceManager().get_all_namespaces()
        self._cs_db = ConnectedState()
        if namespaces and NAMESPACE_MODE:
            self.namespace_mode = True
            self._server_agent = AxonNameSpaceServerAgent()
            self._client_agent = AxonNameSpaceClientAgent()
        else:
            self.namespace_mode = False
            self._server_agent = AxonRootNamespaceServerAgent()
            self._client_agent = AxonRootNamespaceClientAgent()

    def add_server(self, protocol, port, namespace=None):
        if not self.namespace_mode and namespace:
            raise ValueError(
                "namespace parameter must not be provided,"
                "as the Axon is running in non namespace mode")
        self._server_agent.add_server(port, protocol, namespace)

    def register_traffic(self, traffic_configs):
        for config in traffic_configs:
            self._cs_db.create_connected_state(
                config['endpoint'], config['servers'], config['clients'])

    def unregister_traffic(self, endpoint=None):
        self._cs_db.delete_connected_state(endpoint)

    def update_traffic(self, endpoint, traffic_config):
        pass

    def list_servers(self):
        return self._server_agent.list_servers()

    def get_server(self, protocol, port):
        return self._server_agent.get_server(protocol, port)

    def stop_servers(self, namespace=None):
        if not self.namespace_mode and namespace:
            raise ValueError(
                "namespace parameter must not be provided,"
                "as the Axon is running in non namespace mode")
        self._server_agent.stop_servers(namespace)

    def start_servers(self, namespace=None):
        if not self.namespace_mode and namespace:
            raise ValueError(
                "namespace parameter must not be provided,"
                "as the Axon is running in non namespace mode")
        self._server_agent.start_servers(namespace)

    def stop_server(self, protocol, port, namespace=None):
        if not self.namespace_mode and namespace:
            raise ValueError(
                "namespace parameter must not be provided,"
                "as the Axon is running in non namespace mode")
        self._server_agent.stop_server(protocol, port, namespace)

    def stop_client(self, src):
        self._client_agent.stop_client(src)

    def stop_clients(self, namespace=None):
        if not self.namespace_mode and namespace:
            raise ValueError(
                "namespace parameter must not be provided,"
                "as the Axon is running in non namespace mode")
        self._client_agent.stop_clients(namespace)

    def start_clients(self):
        self._client_agent.start_clients()
