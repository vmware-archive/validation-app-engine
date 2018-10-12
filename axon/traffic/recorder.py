import logging
from axon.db.local import get_session, init_session
from axon.db.local.repository import Repositories


class TrafficRecorder(object):

    def record_traffic(self, record):
        raise NotImplementedError()


class StreamRecorder(TrafficRecorder):
    def record_traffic(self, record):
        print(
            "Traffic:%s Source:%s Destination:%s Latency:%s Success:%s"
            "Error:%s" % (record.traffic_type, record.src,
                          record.dst, record.latency,
                          record.success, record.error))


class LogFileRecorder(TrafficRecorder):
    def __init__(self, log_file):
        super(LogFileRecorder, self).__init__()
        self.log = self._get_logger(log_file)

    def _get_logger(self, log_file):
        log_formatter = logging.Formatter(
            '%(asctime)s::%(message)s')
        root_logger = logging.getLogger(__name__)
        root_logger.setLevel(logging.DEBUG)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(log_formatter)
        root_logger.addHandler(file_handler)
        return root_logger

    def record_traffic(self, record):
        self.log.info(
            "Traffic:%s Source:%s Destination:%s Latency:%s Success:%s "
            "Error:%s" % (record.traffic_type, record.src,
                          record.dst, record.latency,
                          record.success, record.error))


class SqliteDbRecorder(TrafficRecorder):
    def __init__(self):
        super(SqliteDbRecorder, self).__init__()
        init_session()
        self._session = get_session()
        self._repositery = Repositories()

    def record_traffic(self, record):
        self._repositery.create_record(self._session, **record.as_dict())
        self._session.commit()
