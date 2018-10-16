import rpyc


class Controller(rpyc.Service):

    RPYC_PROTOCOL_CONFIG = {}

    def __init__(self):
        super(Controller, self).__init__()

    def on_connect(self, conn):
        print("Connected to %r", conn)

    def on_disconnect(self, conn):
        print("Disconnected from %r", conn)


class AxonController(Controller):

    def __init__(self):
        super(AxonController, self).__init__()


def main():
    # TODO(Raies): Read port from some config file if required
    axon_service_port = 5678

    from rpyc.utils.server import ThreadedServer
    t = ThreadedServer(AxonController(),
                       port=axon_service_port,
                       protocol_config=AxonController.RPYC_PROTOCOL_CONFIG)
    t.daemon = True
    t.start()


if __name__ == '__main__':
    main()
