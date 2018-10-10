import abc
import multiprocessing as mp
import six
import SocketServer
from threading import Thread

from axon.common.consts import REQUEST_QUEUE_SIZE, PACKET_SIZE,\
    ALLOW_REUSE_ADDRESS


@six.add_metaclass(abc.ABCMeta)
class Server(object):
    """
    Base Server Class
    """

    @abc.abstractmethod
    def run(self):
        """
        Start A Server
        :return: None
        """
        pass

    @abc.abstractmethod
    def stop(self):
        """
        Stop a server
        :return: None
        """
        pass

    @abc.abstractmethod
    def is_alive(self):
        """
        Check if server is running
        :return: True or False
        """
        pass


@six.add_metaclass(abc.ABCMeta)
class ServerContainer(object):
    """
    A Thread or Process which holds the Server obj and
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
    def is_alive(self):
        """
        Check if Server Container is alive
        :return: True or False
        """
        pass


class TCPRequestHandler(SocketServer.BaseRequestHandler):
    """
    Handler for TCP Requests.
    If we are using ThreadedTCPServer with the help of
    SocketServer.ThreadingMixIn feature, every TCP request will
    be handled in single thread.
    """

    def handle(self):
        data = self.request.recv(PACKET_SIZE)
        self.request.send(data)


class UDPRequestHandler(SocketServer.BaseRequestHandler):
    """
    Handler for UDP Requests.
    If we are using ThreadedUDPServer with the help of
    SocketServer.ThreadingMixIn feature, every UDP request will
    be handled in single thread.
    """

    def handle(self):
        data = self.request[0].strip()
        socket = self.request[1]
        socket.sendto(data, self.client_address)


class ThreadedTCPServer(SocketServer.ThreadingMixIn,
                        SocketServer.TCPServer, Server):
    """
    This is a TCP Server which will handle every single client request
    in separate thread.
    """
    allow_reuse_address = ALLOW_REUSE_ADDRESS
    request_queue_size = REQUEST_QUEUE_SIZE

    def run(self):
        self.serve_forever()

    def stop(self):
        self.shutdown()
        self.server_close()

    def is_alive(self):
        pass


class ThreadedUDPServer(SocketServer.ThreadingMixIn,
                        SocketServer.UDPServer, Server):
    """
    This is a UDP Server which will handle every single client request
    in separate thread.
    """
    allow_reuse_address = ALLOW_REUSE_ADDRESS
    request_queue_size = REQUEST_QUEUE_SIZE

    def run(self):
        self.serve_forever()

    def stop(self):
        self.shutdown()
        self.server_close()

    def is_alive(self):
        pass


class ServerThread(Thread, ServerContainer):
    """
    Run A Server Inside a thread
    """

    def __init__(self, server_obj):
        super(ServerThread, self).__init__()
        self.daemon = True
        self._server_obj = server_obj

    def run(self):
        self._server_obj.run()

    def stop(self):
        self._server_obj.stop()

    def is_alive(self):
        pass


class ServerProcess(mp.Process, ServerContainer):
    """
    Run a server inside a process
    """
    def __init__(self, server_obj):
        super(ServerProcess, self).__init__()
        self._server_obj = server_obj

    def run(self):
        self._server_obj.run()

    def stop(self):
        self.terminate()

    def is_alive(self):
        pass
