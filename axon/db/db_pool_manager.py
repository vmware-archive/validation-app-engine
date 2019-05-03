import logging
from multiprocessing.pool import ThreadPool

from axon.db.recorder_factory import RecorderFactory
from axon.common import config as conf


log = logging.getLogger(__name__)


def process_record_queues(args):
    queue = args[0]
    recorder = args[1]
    while True:
        try:
            t_record = queue.get()
            recorder.record_traffic(t_record)
        except Exception:
            log.exception("Error in listening Traffic Record Queue")


class DBPoolManager(object):
    """
    This class act as a deamon to read traffic record queue and to
    write record to the db recorder provided
    """

    def __init__(self, record_queue):
        self._db_recorder = RecorderFactory.get_recorder()
        self._record_queue = record_queue

    def run(self):
        thread_pool = ThreadPool(conf.RECORD_UPDATER_THREAD_POOL_SIZE)
        thread_pool.map(process_record_queues,
                        [(self._record_queue,
                          self._db_recorder)] *
                        conf.RECORD_UPDATER_THREAD_POOL_SIZE)
