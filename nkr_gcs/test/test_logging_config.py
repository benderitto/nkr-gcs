import logging

from nkr_gcs.logging_config import configure_logging


def test_configure_logging_creates_bounded_utf8_file(tmp_path):
    path = tmp_path / "NKR-GCS" / "nkr-gcs.log"
    configure_logging(path)

    logging.getLogger("nkr_gcs.test").info("diagnostic sentinel")
    for handler in logging.getLogger().handlers:
        handler.flush()

    assert "diagnostic sentinel" in path.read_text(encoding="utf-8")
    handlers = [
        handler for handler in logging.getLogger().handlers
        if isinstance(handler, logging.FileHandler)
        and handler.baseFilename == str(path)
    ]
    assert len(handlers) == 1
    assert handlers[0].maxBytes == 2 * 1024 * 1024
