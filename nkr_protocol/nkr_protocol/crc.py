"""
NKR Protocol CRC16-CCITT-FALSE

Polynomial : 0x1021
Init value : 0xFFFF
RefIn      : False
RefOut     : False
XorOut     : 0x0000
"""


def crc16(data: bytes) -> int:
    crc = 0xFFFF

    for byte in data:

        crc ^= byte << 8

        for _ in range(8):

            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc <<= 1

            crc &= 0xFFFF

    return crc