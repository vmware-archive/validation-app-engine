import logging
import multiprocessing as mp

from axon.traffic.recorder import SqliteDbRecorder
from axon.traffic.connected_state import ConnectedStateProcessor, \
    DBConnectedState
from axon.traffic.agents import AxonRootNamespaceClientAgent,\
    AxonRootNamespaceServerAgent, AxonNameSpaceClientAgent,\
    AxonNameSpaceServerAgent
from axon.utils.network_utils import NamespaceManager


class DBManagerProcess(object):
    """
    This class act as a deamon process to read traffic record queue and to
    write record to the db recorder provided
    """
    def __init__(self, db_recorder=None):
        self._db_recorder = db_recorder if db_recorder else SqliteDbRecorder()
        self.log = logging.getLogger(__name__)

    def process_record_queues(self, r_queue):
        self.log.info("Start listening Traffic Record Queue")
        while True:
            try:
                t_record = r_queue.get()
                self.record_traffic_to_recorder(t_record)
            except:
                self.log.exception("Error in listening Traffic Record Queue")

    def record_traffic_to_recorder(self, t_record):
        # TODO add insert Batch insert to reduce database RTT
        self._db_recorder.record_traffic(t_record)


class TrafficApp(object):
    def __init__(self, config):
        self.log = logging.getLogger(__name__)
        self._conf = config
        # Initiate the traffic record queue
        self.tr_queue = mp.Queue(200)
        self.deamon_obj = DBManagerProcess(self._conf.TRAFFIC_RECORDER)
        # daemon process to check record queue
        self.db_manager = mp.Process(
            target=self.deamon_obj.process_record_queues,
            args=(self.tr_queue,), name="db_manager_run")
        self.db_manager.daemon = True
        self.db_manager.start()
        self._cs_db = ConnectedStateProcessor(DBConnectedState())
        namespaces = NamespaceManager().get_all_namespaces()
        if namespaces and self._conf.NAMESPACE_MODE:
            self.namespace_mode = True
            self._server_agent = AxonNameSpaceServerAgent()
            self._client_agent = AxonNameSpaceClientAgent(
                tr_queue=self.tr_queue)
        else:
            self.namespace_mode = False
            self._server_agent = AxonRootNamespaceServerAgent()
            self._client_agent = AxonRootNamespaceClientAgent(
                tr_queue=self.tr_queue)

    def add_server(self, protocol, port, endpoint, namespace=None):
        if not self.namespace_mode and namespace:
            raise ValueError(
                "namespace parameter must not be provided,"
                "as the Axon is running in non namespace mode")
        self.log.info("Add %s Server on port %s started" % (protocol, port))
        self._server_agent.add_server(port, protocol, endpoint, namespace)

    def register_traffic(self, traffic_configs):
        self.log.info("Register traffic called with config %s" %
                      traffic_configs)

        for config in traffic_configs:
            self._cs_db.create_or_update_connected_state(
                config['endpoint'],
                config['servers'],
                config['clients'])

    def unregister_traffic(self, traffic_configs):
        self.log.info("Un-Register traffic called with config %s" %
                      traffic_configs)
        for config in traffic_configs:
            self._cs_db.delete_connected_state(
                config.get('endpoint'),
                config.get('servers', []),
                config.get('clients', []))

    def get_traffic_config(self, endpoint=None):
        return self._cs_db.get_connected_state(endpoint)

    def list_servers(self):
        return self._server_agent.list_servers()

    def get_server(self, protocol, port):
        return self._server_agent.get_server(protocol, port)

    def stop_servers(self, namespace=None):
        self.log.info("=====Stop servers called=====")
        if not self.namespace_mode and namespace:
            raise ValueError(
                "namespace parameter must not be provided,"
                "as the Axon is running in non namespace mode")
        self._server_agent.stop_servers(namespace)

    def start_servers(self, namespace=None):
        self.log.info("=====Start servers called=====")
        if not self.namespace_mode and namespace:
            raise ValueError(
                "namespace parameter must not be provided,"
                "as the Axon is running in non namespace mode")
        self._server_agent.start_servers(namespace)

    def stop_server(self, protocol, port, namespace=None):
        self.log.info("stop %s server called on port %s" % (protocol, port))
        if not self.namespace_mode and namespace:
            raise ValueError(
                "namespace parameter must not be provided,"
                "as the Axon is running in non namespace mode")
        self._server_agent.stop_server(protocol, port, namespace)

    def stop_client(self, namespace=None):
        self.log.info("====stop client initiated====")
        if not self.namespace_mode and namespace:
            raise ValueError(
                "namespace parameter must not be provided,"
                "as the Axon is running in non namespace mode")
        self._client_agent.stop_client(namespace)

    def stop_clients(self, namespace=None):
        self.log.info("====stop clients initiated====")
        if not self.namespace_mode and namespace:
            raise ValueError(
                "namespace parameter must not be provided,"
                "as the Axon is running in non namespace mode")
        self._client_agent.stop_clients(namespace=namespace)

    def start_clients(self):
        self.log.info("====start clients initiated====")
        self._client_agent.start_clients()
