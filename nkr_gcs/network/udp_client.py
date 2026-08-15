import socket


class UDPClient:

    def __init__(
        self,
        host: str,
        port: int,
    ):

        self.address = (host, port)

        self.sock = self._new_socket()

    @staticmethod
    def _new_socket():
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setblocking(False)
        return sock

    def send(
        self,
        data: bytes,
    ):

        return self.sock.sendto(data, self.address)

    def receive(self, size: int = 1024) -> list[bytes]:
        """Drain pending datagrams without ever blocking the UI thread."""
        packets = []
        while True:
            try:
                data, _address = self.sock.recvfrom(size)
            except BlockingIOError:
                return packets
            packets.append(data)

    def close(self):

        self.sock.close()

    def reopen(self):
        """Replace a failed socket; the new source port requires a new session."""
        self.sock.close()
        self.sock = self._new_socket()
