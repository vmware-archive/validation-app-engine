from axon.utils.network_utils import NamespaceManager


class NamespaceApp(object):
    def __init__(self):
        self._ns_manager = NamespaceManager()

    def list_namespaces(self):
        return self._ns_manager.get_all_namespaces()

    def get_namespace(self, namespace):
        return self._ns_manager.get_namespace(namespace)
