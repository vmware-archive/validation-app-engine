import rpyc

from axon.apps.traffic import TrafficApp
from axon.apps.stats import StatsApp
from axon.apps.namespace import NamespaceApp
from axon.apps.interface import InterfaceApp

rpyc.core.protocol.DEFAULT_CONFIG['allow_pickle'] = True


def exposify(cls):
    for key in dir(cls):
        val = getattr(cls, key)
        if callable(val) and not key.startswith("_"):
            setattr(cls, "exposed_%s" % (key,), val)
    return cls


class RPyCService(rpyc.Service):

    RPYC_PROTOCOL_CONFIG = rpyc.core.protocol.DEFAULT_CONFIG

    def __init__(self):
        super(RPyCService, self).__init__()

    def on_connect(self, conn):
        print("Connected to %r", conn)

    def on_disconnect(self, conn):
        print("Disconnected from %r", conn)


@exposify
class exposed_Traffic(TrafficApp):
    pass


@exposify
class exposed_Stats(StatsApp):
    pass


@exposify
class exposed_Namespace(NamespaceApp):
    pass


@exposify
class exposed_Interface(InterfaceApp):
    pass


class AxonControlService(RPyCService):

    def __init__(self):
        super(AxonControlService, self).__init__()
        self.exposed_traffic = exposed_Traffic()
        self.exposed_stats = exposed_Stats()
        self.exposed_namespace = exposed_Namespace()
        self.exposed_interface = exposed_Interface()


if __name__ == '__main__':
    from rpyc.utils.server import ThreadedServer
    t = ThreadedServer(AxonControlService(),
                       port=5678,
                       protocol_config=AxonControlService.RPYC_PROTOCOL_CONFIG)
    t.start()
