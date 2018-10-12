import time


class TrafficRecord:
    """
    Class to represent TrafficRecord
    """
    TRAFFIC_TYPE = None

    def __init__(self, src, dst, port, latency, error=None, success=True):
        self.src = src
        self.dst = dst
        self.port = port
        self.latency = latency
        self.error = error
        self.success = success
        self.traffic_type = self.TRAFFIC_TYPE
        self.created_time = time.time()

    def as_dict(self):
        return {
            'source': self.src, 'destination': self.dst, 'port': self.port,
            'latency': self.latency, 'error': self.error,
            'success': self.success, 'type': self.traffic_type,
            'created_time': self.created_time

        }


class TCPRecord(TrafficRecord):
    """
    TCP Traffic record
    """
    TRAFFIC_TYPE = "TCP"


class UDPRecord(TrafficRecord):
    """
    UDP Traffic Record
    """
    TRAFFIC_TYPE = "UDP"
