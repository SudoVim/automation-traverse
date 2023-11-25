import unittest
from unittest.mock import MagicMock, call
from .simple_log import SimpleLogEmitter
from .emitter import LogLevel
import colorama


class MockEmitter(SimpleLogEmitter):
    emit_mock: MagicMock

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.emit_mock = MagicMock()

    def emit(self, message: str) -> None:
        self.emit_mock(message)


class SimpleLogTestCase(unittest.TestCase):
    emitter: MockEmitter

    def setUp(self) -> None:
        self.emitter = MockEmitter()


class TestLogMessage(SimpleLogTestCase):
    def test_no_color(self) -> None:
        self.emitter.use_color = False
        self.emitter.log_message(LogLevel.INFO, "message")

        self.emitter.emit_mock.assert_called_once_with("message\n")

    def test_with_color(self) -> None:
        self.emitter.log_message(LogLevel.INFO, "message")

        self.emitter.emit_mock.assert_called_once_with(
            f"{colorama.Fore.WHITE}message{colorama.Style.RESET_ALL}\n"
        )

    def test_multiline(self) -> None:
        self.emitter.use_color = False
        self.emitter.log_message(LogLevel.INFO, "message1\nmessage2")

        self.assertEqual(
            [
                call("message1\n"),
                call("message2\n"),
            ],
            self.emitter.emit_mock.mock_calls,
        )

    def test_spaces(self) -> None:
        self.emitter.use_color = False
        self.emitter.context_level = 2
        self.emitter.log_message(LogLevel.INFO, "message")

        self.emitter.emit_mock.assert_called_once_with(" " * 8 + "message\n")

    def test_end(self) -> None:
        self.emitter.use_color = False
        self.emitter.log_message(LogLevel.INFO, "message", end="#")

        self.emitter.emit_mock.assert_called_once_with("message#")

    def test_end_multiline(self) -> None:
        self.emitter.use_color = False
        self.emitter.log_message(LogLevel.INFO, "message1#message2", end="#")

        self.assertEqual(
            [
                call("message1#"),
                call("message2#"),
            ],
            self.emitter.emit_mock.mock_calls,
        )
