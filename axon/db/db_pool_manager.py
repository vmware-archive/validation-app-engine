import logging
from multiprocessing.pool import ThreadPool

from axon.db.recorder import SqlDbRecorder


POOL_SIZE = 20
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

    def __init__(self, record_queue, db_recorder=None):
        self._db_recorder = db_recorder if db_recorder else SqlDbRecorder()
        self._record_queue = record_queue

    def run(self):
        thread_pool = ThreadPool(POOL_SIZE)
        thread_pool.map(process_record_queues,
                        [(self._record_queue, self._db_recorder)] * POOL_SIZE)
