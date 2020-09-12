
import socket
import time

from grus.traffic.connection import Connection


class PingValidationError(Exception):
    pass

class Client(Connection):
    PAYLOAD = 'Dunkirk!!'
    PING_INTERVAL = 2   # default request rate is 30ppm
    CONNECTION_TIMEOUT = 2

    def __init__(self, server, port, verbose=False, handler=None,
                 interval=None):
        """
        A simple TCP client which binds to a specified host and port.
        """
        self.server = server
        self.port = port
        try:
            self.interval = int(interval)
        except (ValueError, TypeError) as err:
            _ = err
            self.interval = self.PING_INTERVAL
        self._handler = self.echo_validator if handler is None else handler
        super(Client, self).__init__(verbose=verbose)

    def echo_validator(self, payload, data):
        """
        Ping Validator
        """
        try:
            assert(data == self.PAYLOAD)
        except AssertionError as err:
            _ = err
            raise PingValidationError()

    def start(self, payload=None, tries=None):
        payload = self.PAYLOAD if payload is None else payload
        try:
            tries = int(tries) if tries is not None else None
        except Exception as err:
            _ = err
            tries = None

        while not self.is_event_set():
            if tries is not None:
                if not tries:
                    break
                else:
                    tries -= 1
            self.ping(payload)
            if self.interval:
                time.sleep(self.interval)

class TCPClient(Client):

    def _create_socket(self):
        """
        Returns a simple TCP server socket.
        """
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(self.CONNECTION_TIMEOUT)

    def ping(self, payload):
        data = None
        try:
            # create socket
            self._create_socket()
            self.socket.connect((self.server, self.port))
            self.socket.settimeout(None)
            self.socket.send(payload)
            data = self.socket.recv(self.MAX_PAYLOAD_SIZE)
            # close socket connection
            self.socket.close()

            if self.verbose:
                msg = "ping to %s:%s pass. data - %r" % (
                    self.server, self.port, data)
                # self.log.info(msg)
            return data  # TODO : is is needed ?
        except Exception as err:
            msg = "ping to %s:%s failed. Error - %r" % (
                self.server, self.port, err)
            if self.verbose:
                self.log.error(msg)
        finally:
            self._handler(payload, data)

class UDPClient(Client):

    def _create_socket(self):
        """
        Returns a simple TCP server socket.
        """
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.settimeout(self.CONNECTION_TIMEOUT)

    def ping(self, payload):
        try:
            # create socket
            self._create_socket()
            addr = (self.server, self.port)
            self.socket.sendto(payload, addr)
            try:
                data, server = self.socket.recvfrom(self.MAX_PAYLOAD_SIZE)
            except Exception:
                data, server = None, None
            _ = server
            # close socket connection
            self.socket.close()

            if self.verbose:
                msg = "ping to %s:%s pass. data - %r" % (
                    self.server, self.port, data)
                self.log.info(msg)
            return data
        except Exception as err:
            self.log.error("ping to %s:%s failed. Error - %r",
                           self.server, self.port, err)
            # TODO : check if raise is an issue.
            # return False
            raise
        finally:
            self._handler(payload, data)