from axon.utils.network_utils import InterfaceManager


class InterfaceApp(object):
    def __init__(self):
        self._if_mngr = InterfaceManager()

    def list_interfaces(self):
        return self._if_mngr.get_all_interfaces()

    def get_interface(self, name):
        return self._if_mngr.get_interface(name)
