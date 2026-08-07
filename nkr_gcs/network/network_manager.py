from nkr_protocol.nkr_protocol.protocol import pack_control
from nkr_protocol.nkr_protocol.packets import ControlPacket

from .udp_client import UDPClient


class NetworkManager:

    def __init__(self):

        self.client = UDPClient()

        self.sequence = 0

    def update(self, operator):

        packet = ControlPacket()

        packet.sequence = self.sequence

        packet.throttle = int(
            operator.throttle * 1000
        )

        packet.steering = int(
            operator.steering * 1000
        )

        packet.brake = int(
            operator.brake * 1000
        )

        packet.requested_mode = operator.requested_drive_mode

        packet.buttons = operator.buttons
        
        packet.buttons_changed = operator.buttons_changed

        raw = pack_control(packet)

        self.client.send(raw)

        self.sequence = (
            self.sequence + 1
        ) & 0xFFFF