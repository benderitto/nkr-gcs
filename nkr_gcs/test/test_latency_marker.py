from nkr_gcs.video.latency_marker import (
    PREAMBLE,
    TIMESTAMP_BITS,
    calculate_video_latency_ms,
    decode_timestamp_ticks,
    measure_video_latency_ms,
)


def _levels_for_timestamp(timestamp_ms, dark=18, light=238):
    binary = (timestamp_ms // 10) % (1 << TIMESTAMP_BITS)
    gray = binary ^ (binary >> 1)
    bits = list(PREAMBLE) + [
        (gray >> bit) & 1 for bit in range(TIMESTAMP_BITS)
    ]
    return [light if bit else dark for bit in bits]


def test_decodes_gray_coded_unix_centiseconds_across_periods():
    captured_ms = 1_786_820_123_450
    levels = _levels_for_timestamp(captured_ms)

    assert decode_timestamp_ticks(levels) == (
        captured_ms // 10
    ) % (1 << TIMESTAMP_BITS)
    assert calculate_video_latency_ms(levels, captured_ms + 73) == 73


def test_adaptive_threshold_tolerates_compression_levels():
    captured_ms = 1_786_820_123_450
    levels = _levels_for_timestamp(captured_ms, dark=54, light=185)

    assert decode_timestamp_ticks(levels) is not None


def test_rejects_missing_marker_and_implausible_delay():
    captured_ms = 1_786_820_123_450
    levels = _levels_for_timestamp(captured_ms)
    levels[0] = levels[1]

    assert decode_timestamp_ticks(levels) is None
    assert calculate_video_latency_ms(
        _levels_for_timestamp(captured_ms), captured_ms + 10_001,
    ) is None
    assert calculate_video_latency_ms(
        _levels_for_timestamp(captured_ms), None,
    ) is None


def test_rejects_future_frame_instead_of_reporting_zero():
    captured_ms = 1_786_820_123_450
    levels = _levels_for_timestamp(captured_ms)

    assert measure_video_latency_ms(levels, captured_ms - 100) == -100
    assert calculate_video_latency_ms(levels, captured_ms - 100) is None
