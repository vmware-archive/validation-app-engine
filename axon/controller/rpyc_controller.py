import rpyc
from rpyc.utils.server import ThreadedServer


class AxonServiceBase(rpyc.Service):

    RPYC_PROTOCOL_CONFIG = {}

    def __init__(self):
        super(AxonServiceBase, self).__init__()

    def on_connect(self, conn):
        print("Connected to %r", conn)

    def on_disconnect(self, conn):
        print("Disconnected from %r", conn)


class AxonService(AxonServiceBase):

    def __init__(self):
        super(AxonService, self).__init__()


class AxonController(object):

    def __init__(self):
        # TODO(Raies): Need tp read port from some conf file
        self.axon_port = 5678
        self.service_cls = AxonService()
        self.service_cls.daemon = True
        self.protocol_config = self.service_cls.RPYC_PROTOCOL_CONFIG
        self.axon_service = ThreadedServer(
            self.service_cls,
            port=self.axon_port,
            reuse_addr=True,
            protocol_config=self.protocol_config)

    def start(self):
        self.axon_service.start()

    def stop(self):
        self.axon_service.close()


def main():
    axon_service = AxonController()
    axon_service.start()


if __name__ == '__main__':
    main()
