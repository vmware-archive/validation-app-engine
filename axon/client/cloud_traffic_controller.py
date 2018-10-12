from axon.client.traffic_controller import TrafficController
from axon.client.axon_client import AxonClient


class TrafficRecord(object):
    def __init__(self, endpoint, servers=None, clients=None):
        self._endpoint = endpoint
        self._servers = servers if servers else []
        self._clients = clients if clients else []

    def add_server(self, protocol, port):
        if (protocol, port) not in self._servers:
            self._servers.append((protocol, port))

    def add_client(self, protocol, port, destination, connected):
        if (protocol, port, destination) not in self._clients:
            self._clients.append((protocol, port, destination, connected))

    def as_dict(self):
        return dict(zip(['endpoint', 'servers', 'clients'],
                        [self._endpoint, self._servers, self._clients]))


class CloudTrafficController(TrafficController):

    def __init__(self, gateway_host=None):
        super(CloudTrafficController, self).__init__()
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
                dst, bool(trule.action))
        for server, rule in self._servers.items():
            print "pushing on server %s" %server
            with AxonClient(server, proxy_host=self._gw_host) as client:
                client.traffic.register_traffic([rule.as_dict()])

    def unregister_traffic(self, traffic_config):
        pass

    def stop_traffic(self):
        for server in self._servers.keys():
            with AxonClient(server, proxy_host=self._gw_host) as client:
                client.traffic.stop_clients()
        for server in self._servers.keys():
            with AxonClient(server, proxy_host=self._gw_host) as client:
                client.traffic.stop_servers()

    def start_traffic(self):
        for server in self._servers.keys():
            with AxonClient(server, proxy_host=self._gw_host) as client:
                client.traffic.start_servers()
        for server in self._servers.keys():
            with AxonClient(server, proxy_host=self._gw_host) as client:
                client.traffic.start_clients()

    def restart_traffic(self):
        self.stop_traffic()
        self.start_traffic()
