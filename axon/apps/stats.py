from axon.db.local import get_session, init_session
from axon.db.local.repository import Repositories


class StatsApp(object):
    def __init__(self):
        init_session()
        self._repository = Repositories()

    def get_failure_count(self, start_time=None, end_time=None,
                          destination=None, port=None):
        filters = {'success': False}
        if port:
            filters['port'] = port
        if destination:
            filters['destination'] = destination
        if not start_time and not end_time:
            return len(self._repository.record.get_all(
                get_session(), **filters))
        else:
            return self._repository.record.get_failure_count(
                get_session(), start_time, end_time, **filters)

    def get_success_count(self, start_time=None, end_time=None,
                          destination=None, port=None):
        filters = {'success': True}
        if port:
            filters['port'] = port
        if destination:
            filters['destination'] = destination

        if not start_time and not end_time:
            return len(self._repository.record.get_all(
                get_session(), **filters))
        else:
            return self._repository.record.get_success_count(
                get_session(), start_time, end_time, **filters)
