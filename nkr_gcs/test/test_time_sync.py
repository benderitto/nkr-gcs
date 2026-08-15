import struct

from nkr_gcs.time_sync import (
    NTP_PACKET_SIZE,
    _encode_ntp_timestamp,
    parse_sntp_response,
)


def test_sntp_four_timestamp_offset_and_round_trip():
    sent_at = 1_786_820_000.000
    server_received = sent_at + 0.060
    server_sent = server_received + 0.001
    received_at = sent_at + 0.101
    request_timestamp = _encode_ntp_timestamp(sent_at)
    packet = bytearray(NTP_PACKET_SIZE)
    packet[0] = 0x24  # Version 4, server mode.
    packet[1] = 2
    packet[24:32] = request_timestamp
    packet[32:40] = _encode_ntp_timestamp(server_received)
    packet[40:48] = _encode_ntp_timestamp(server_sent)

    offset, round_trip = parse_sntp_response(
        bytes(packet), request_timestamp, sent_at, received_at,
    )

    assert round(offset * 1000) == 10
    assert round(round_trip * 1000) == 100


def test_sntp_rejects_unmatched_response():
    packet = bytearray(NTP_PACKET_SIZE)
    packet[0] = 0x24
    packet[1] = 2
    packet[24:32] = struct.pack("!Q", 1)

    try:
        parse_sntp_response(bytes(packet), struct.pack("!Q", 2), 1.0, 2.0)
    except ValueError as exc:
        assert "mismatch" in str(exc)
    else:
        raise AssertionError("unmatched SNTP response was accepted")
