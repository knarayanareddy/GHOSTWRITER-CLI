import logging

from gw.logging import SanitizingFormatter


def test_sanitizing_formatter_redacts_credentials_and_paths():
    formatter = SanitizingFormatter()
    record = logging.LogRecord("x", logging.INFO, __file__, 1, "token=supersecret path=/home/alice/private/corpus.txt", (), None)
    line = formatter.format(record)
    assert "supersecret" not in line
    assert "/home/alice" not in line
    assert "<redacted>" in line
