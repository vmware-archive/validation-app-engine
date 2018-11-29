import abc
import datetime
import itertools
import six
import socket
from threading import Thread
import time
import logging

from axon.common.consts import PACKET_SIZE
from axon.traffic.resources import TCPRecord, UDPRecord


@six.add_metaclass(abc.ABCMeta)
class Client(object):

    @abc.abstractmethod
    def ping(self):
        """
        Send the traffic to a endpoint
        :return:  None
        """
        pass

    @abc.abstractmethod
    def record(self):
        """
        Record the data to a data source
        :return: None
        """
        pass


class TCPClient(Client):
    def __init__(self, source, destination, port, connected=True,
                 action=1, request_count=1, tr_queue=None):
        """
        Client to send TCP requests
        :param source: source ip
        :type source: string
        :param destination: destination ip
        :type destination: str
        :param port: destination server port
        :type port: int
        :param connected: whether endpoints are connected or not
        :type connected: bool
        :param action: whether traffic will be accepted or rejected by server
                      i.e. 0 for reject and 1 for allow
        :type action: int
        :param tr_queue: traffic record queue
        :type tr_queue: Queue
        """
        self.log = logging.getLogger(__name__)
        self._source = source
        self._port = port
        self._destination = destination
        self._start_time = None
        self._request_count = request_count
        self._connected = connected
        self._action = action
        self._tr_queue = tr_queue

    def _create_socket(self, address_family=socket.AF_INET,
                       socket_type=socket.SOCK_STREAM):
        """
        Creates a socket
        :param address_family: address family
        :type address_family: socket address family object
        :param socket_type: type of the socket i.e. STREAM or DATAGRAM
        :type socket_type: socket type object
        :return: created socket
        :rtype: socket object
        """
        sock = socket.socket(address_family, socket_type)
        sock.settimeout(2)
        return sock

    def __connect(self, sock):
        """
        Create a connection to the server
        :param sock: socket object
        :type sock: socket
        """
        sock.connect((self._destination, self._port))

    def _send_receive(self, sock, payload):
        """
        Send and recieve the packet
        :param sock: socket which is connected to server
        :type sock: socket
        :param payload: data to be send
        :type payload: str
        :return: data returned from server
        :rtype: str
        """
        try:
            sock.send(payload)
            sock.recv(PACKET_SIZE)
        except:
            raise
        finally:
            sock.close()

    def _get_latency(self):
        """
        Get latency of the request
        :return: latency of the request
        :rtype: float
        """
        time_diff = datetime.datetime.now() - self._start_time
        return time_diff.seconds * 1000 + time_diff.microseconds * .001

    def is_traffic_successful(self, success):
        if not bool(self._connected):
            result = bool(self._connected) == bool(success)
        else:
            # change it later, when action accepts more values
            result = bool(self._action) == bool(success)
        return result

    def record(self, success=True, error=None):
        """
        Record the traffic to data source
        :return: None
        """
        success = self.is_traffic_successful(success)
        record = TCPRecord(
            self._source, self._destination, self._port,
            self._get_latency(),
            error, success, self._connected)
        try:
            self._tr_queue.put(record)
        except:
            self.log.exception("Exception while adding TCP record for src "
                               "{0} and dst {1} to traffic queue {2}".format(
                                self._source, self._destination,
                                self._tr_queue))

    def ping(self):
        # TODO(pksingh) Decide on payload
        payload = 'Dinkirk'.encode()
        for _ in range(self._request_count):
            try:
                self._start_time = datetime.datetime.now()
                sock = self._create_socket()
                self.__connect(sock)
                self._send_receive(sock, payload)
                self.record()
            except Exception as e:
                self.record(success=False, error=str(e))


class UDPClient(TCPClient):

    def ping(self):
        # TODO(pksingh) Decide on payload
        payload = 'Dinkirk'.encode()
        for _ in range(self._request_count):
            try:
                self._start_time = datetime.datetime.now()
                sock = self._create_socket(socket.AF_INET, socket.SOCK_DGRAM)
                self._send_receive(sock, payload)
                self.record()
            except Exception as e:
                self.record(success=False, error=str(e))

    def _send_receive(self, sock, payload):
        """
        Send and receive the packet
        :param sock: socket which is connected to server
        :type sock: socket
        :param payload: data to be send
        :type payload: str
        :return: data returned from server
        :rtype: str
        """
        try:
            sock.sendto(payload, (self._destination, self._port))
            sock.recvfrom(PACKET_SIZE)
        except:
            raise
        finally:
            sock.close()

    def record(self, success=True, error=None):
        """
        Record the traffic to data source
        :return: None
        """
        success = self.is_traffic_successful(success)
        record = UDPRecord(
            self._source, self._destination, self._port,
            self._get_latency(), error, success, self._connected)
        self.log.info("Adding UDP record to queue {0} {1}".format(
            self._tr_queue, record))
        try:
            self._tr_queue.put(record)
        except:
            self.log.exception("Exception while adding TCP record for src "
                               "{0} and dst {1} to traffic queue {2}".format(
                                self._source,
                                self._destination,
                                self._tr_queue))


class TrafficClient(object):

    def __init__(self, src, destinations, request_rate=100, tr_queue=None):
        self._src = src
        self._request_rate = min(request_rate, len(destinations))
        self._destinations = itertools.cycle(destinations)
        self._tr_queue = tr_queue

    def _send_traffic(self):
        threads = []

        for _ in range(self._request_rate):
            protocol, port, endpoint, connected, action = \
                next(self._destinations)
            if protocol == "TCP":
                client = TCPClient(
                    self._src, endpoint, port,
                    connected, action, tr_queue=self._tr_queue)
            if protocol == "UDP":
                client = UDPClient(
                    self._src, endpoint, port,
                    connected, action, tr_queue=self._tr_queue)
            thread = Thread(target=client.ping)
            thread.daemon = True
            thread.start()
            threads.append(thread)
        for thread in threads:
            thread.join()

    def run(self):
        while True:
            self._send_traffic()
            time.sleep(20)
