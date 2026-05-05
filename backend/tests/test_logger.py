import io
import sys
import unittest

from src.lib.logger import bedrock


class LoggerTests(unittest.TestCase):
    def test_logging_non_ascii_message_does_not_crash_on_cp1252_stdout(self):
        original_stdout = sys.stdout
        stream = io.TextIOWrapper(io.BytesIO(), encoding="cp1252", errors="strict")
        sys.stdout = stream
        try:
            bedrock("tool_call " + chr(0x2192) + " query_db")
        finally:
            sys.stdout = original_stdout


if __name__ == "__main__":
    unittest.main()
