import abc
import multiprocessing as mp
from threading import Thread
import six


@six.add_metaclass(abc.ABCMeta)
class Worker(object):
    """
    A Thread or Process which holds the server/client and
    manages its life cycle
    """

    @abc.abstractmethod
    def run(self):
        """
        Run a server
        :return: None
        """
        pass

    @abc.abstractmethod
    def stop(self):
        """
        Stop the Server inside it
        :return: None
        """
        pass

    @abc.abstractmethod
    def is_running(self):
        """
        Check if Server Container is alive
        :return: True or False
        """
        pass


class WorkerThread(Thread, Worker):
    """
    Run A Server/Client Inside a thread
    """

    def __init__(self, traffic_class, args=(), kwargs=None):
        super(WorkerThread, self).__init__()
        self.__traffic_class = traffic_class
        self.__class_args = args
        self.__class_kwargs = kwargs
        self.__traffic_obj = None

    def run(self):
        self.__traffic_obj = self._traffic_class(
            *self.__class_args, **self.__class_kwargs)
        self.__traffic_obj.run()

    def stop(self):
        self.__traffic_obj.stop()

    def is_running(self):
        return self.isAlive()


class WorkerProcess(mp.Process, Worker):
    """
    Run a server/Client inside a process
    """

    def __init__(self, traffic_class, args=(), kwargs=None):
        super(WorkerProcess, self).__init__()
        self.__traffic_class = traffic_class
        self.__class_args = args
        self.__class_kwargs = kwargs
        self.__traffic_obj = None

    def run(self):
        self.__traffic_obj = self.__traffic_class(
            *self.__class_args, **self.__class_kwargs)
        self.__traffic_obj.run()

    def stop(self):
        self.terminate()

    def is_running(self):
        return self.is_alive()
