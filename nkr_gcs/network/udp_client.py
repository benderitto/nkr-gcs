import socket


class UDPClient:

    def __init__(
        self,
        host="192.168.1.24",
        port=9999,
    ):

        self.address = (host, port)

        self.sock = socket.socket(
            socket.AF_INET,
            socket.SOCK_DGRAM,
        )

    def send(
        self,
        data: bytes,
    ):

        self.sock.sendto(
            data,
            self.address,
        )

    def close(self):

        self.sock.close()
