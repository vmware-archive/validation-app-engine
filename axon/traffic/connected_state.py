from axon.db.local import get_session, init_session
from axon.db.local.repository import Repositories


class ConnectedState(object):
    def __init__(self):
        init_session()
        self._repository = Repositories()

    def create_connected_state(self, endpoint=None,
                               servers=None, clients=None):
        session = get_session()
        self._repository.create_connected_state(
            session, endpoint=endpoint, servers=servers, clients=clients)
        session.commit()

    def get_connected_state(self, endpoint):
        session = get_session()
        return self._repository.connected_state.get_all(
            session, endpoint=endpoint)

    def delete_connected_state(self, endpoint=None):
        session = get_session()
        if endpoint:
            self._repository.connected_state.delete(session, endpoint=endpoint)
        else:
            self._repository.connected_state.delete_all(session)
        session.commit()

    def get_servers(self, endpoint):
        session = get_session()
        return self._repository.connected_state.get_servers(session, endpoint)

    def get_clients(self, endpoint):
        session = get_session()
        return self._repository.connected_state.get_clients(session, endpoint)

    def update_servers(self, endpoint_ip, servers):

        session = get_session()
        self._repository.connected_state.update_servers(
            session, endpoint_ip, servers)

    def update_clients(self, endpoint_ip, clients):
        session = get_session()
        self._repository.connected_state.update_clients(
            session, endpoint_ip, clients)
