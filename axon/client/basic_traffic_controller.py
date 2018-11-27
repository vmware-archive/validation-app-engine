from multiprocessing.pool import ThreadPool

from axon.client.traffic_controller import TrafficController
from axon.client.axon_client import AxonClient


def register_traffic(register_param):
    server = register_param[0]
    rule = register_param[1]
    proxy_host = register_param[2]
    with AxonClient(server, proxy_host=proxy_host) as client:
        client.traffic.register_traffic([rule.as_dict()])


def start_servers(start_param):
    server = start_param[0]
    proxy_host = start_param[1]
    with AxonClient(server, proxy_host=proxy_host) as client:
        client.traffic.start_servers()


def start_clients(start_param):
    server = start_param[0]
    proxy_host = start_param[1]
    with AxonClient(server, proxy_host=proxy_host) as client:
        client.traffic.start_clients()


def stop_servers(stop_param):
    server = stop_param[0]
    proxy_host = stop_param[1]
    with AxonClient(server, proxy_host=proxy_host) as client:
        client.traffic.stop_servers()


def stop_clients(stop_param):
    server = stop_param[0]
    proxy_host = stop_param[1]
    with AxonClient(server, proxy_host=proxy_host) as client:
        client.traffic.stop_clients()


class TrafficRecord(object):
    def __init__(self, endpoint, servers=None, clients=None):
        self._endpoint = endpoint
        self._servers = servers if servers else []
        self._clients = clients if clients else []

    def add_server(self, protocol, port):
        if (protocol, port) not in self._servers:
            self._servers.append((protocol, port))

    def add_client(self, protocol, port, destination, connected, action):
        if (protocol, port, destination) not in self._clients:
            self._clients.append((
                protocol, port, destination, connected, action))

    def as_dict(self):
        return dict(zip(['endpoint', 'servers', 'clients'],
                        [self._endpoint, self._servers, self._clients]))


class BasicTrafficController(TrafficController):

    def __init__(self, gateway_host=None):
        super(BasicTrafficController, self).__init__()
        self._gw_host = gateway_host
        self._servers = dict()

    def register_traffic(self, traffic_config):
        for trule in traffic_config:
            src = str(trule.src_eps.ip_list[0])
            dst = str(trule.dst_eps.ip_list[0])
            if not self._servers.get(src):
                self._servers[str(src)] = TrafficRecord(src)
            if not self._servers.get(str(dst)):
                self._servers[dst] = TrafficRecord(dst)
            self._servers[dst].add_server(trule.protocol, trule.port.port)
            self._servers[src].add_client(
                trule.protocol, trule.port.port,
                dst, trule.connected, trule.action)
        pool = ThreadPool(50)
        params = [(server, rule, self._gw_host) for
                  server, rule in self._servers.items()]
        pool.map(register_traffic, params)
        pool.close()
        pool.join()

    def unregister_traffic(self, traffic_config):
        pass

    def __stop_clients(self, servers):
        servers = servers if servers else self._servers.keys()
        if not servers:
            return
        pool = ThreadPool(50)
        params = [(server, self._gw_host) for server in servers]
        pool.map(stop_clients, params)
        pool.close()
        pool.join()

    def __stop_servers(self, servers):
        servers = servers if servers else self._servers.keys()
        if not servers:
            return
        pool = ThreadPool(50)
        params = [(server, self._gw_host) for server in servers]
        pool.map(stop_servers, params)
        pool.close()
        pool.join()

    def __start_servers(self, servers):
        servers = servers if servers else self._servers.keys()
        if not servers:
            return
        pool = ThreadPool(50)
        params = [(server, self._gw_host) for server in servers]
        pool.map(start_servers, params)
        pool.close()
        pool.join()

    def __start_clients(self, servers):
        servers = servers if servers else self._servers.keys()
        if not servers:
            return
        pool = ThreadPool(50)
        params = [(server, self._gw_host) for server in servers]
        pool.map(start_clients, params)
        pool.close()
        pool.join()

    def stop_traffic(self, servers=None):
        self.__stop_clients(servers)
        self.__stop_servers(servers)

    def start_traffic(self, servers=None):
        self.__start_servers(servers)
        self.__start_clients(servers)

    def restart_traffic(self, servers=None):
        self.stop_traffic(servers)
        self.start_traffic(servers)
