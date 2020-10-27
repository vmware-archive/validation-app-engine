import socket
import time

from grus.traffic.connection import Connection

class Server(Connection):

    def __init__(self, port=None, max_conns=None,
                 handler=None, verbose=False, _log=None):
        """
        A basic TCP Server connection listener with default echo reply
        message handler.
        """
        self.host = ''   # blank on server side
        self.port = self.DEFAULT_TCP_SERVER_PORT if port is None else port
        self.max_conns = self.MAX_CONNS if max_conns is None else max_conns
        self._handler = self.echo_handler if handler is None else handler

        super(Server, self).__init__(verbose=verbose)

        # Don't create a socket until we are ready to bind.
        self.socket = None
        if _log:
            self.log = _log


class TCPServer(Server):

    def _create_socket(self):
        """
        Returns a simple TCP server socket.
        """
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    def start(self):
        """
        API to start server at the requested port and other settings.
        """
        try:
            # Create a socket
            self._create_socket()

            # Bind ot the port
            self.socket.bind((self.host, self.port))

            # accept call from client
            self.socket.listen(self.max_conns)

            if self.verbose:  # TODO : more stringent check
                self.log.info(
                    "TCP Server started on %s:%s",
                    self.host,
                    self.port)

            while not self.is_event_set():
                conn, addr = self.socket.accept()
                if self.verbose:
                    msg = "Connection request received from: %s:%s" % addr
                    self.log.info(msg)
                self._handler(conn)
        except Exception as err:
            _ = err
            pass
        finally:
            self.close()

    def close(self):
        if self.socket:
            self.socket.close()
            self.socket = None

    def echo_handler(self, conn):
        """
        A simple default echo message handler.
        """
        data = conn.recv(self.MAX_PAYLOAD_SIZE)
        conn.send(data)  # send same data back as echo
        conn.close()    # close immediately.


class UDPServer(Server):

    def _create_socket(self):
        """
        Returns a simple TCP server socket.
        """
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def start(self):
        """
        API to start server at the requested port and other settings.
        """
        # Create a socket
        self._create_socket()

        # Bind ot the port
        self.socket.bind((self.host, self.port))

        if self.verbose:  # TODO : more stringent check
            self.log.info("UDP Server started on %s:%s", self.host, self.port)

        while not self.is_event_set():
            data, addr = self.socket.recvfrom(self.MAX_PAYLOAD_SIZE)
            if self.verbose:
                msg = "Connection request received from: %s:%s" % addr
                self.log.info(msg)
            self._handler(data, addr)

        self.socket.close()

    def echo_handler(self, data, addr):
        """
        A simple default echo message handler.
        """
        if data:
            self.socket.sendto(data, addr)  # send same data back as echo