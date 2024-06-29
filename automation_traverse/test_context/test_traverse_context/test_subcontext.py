from unittest.mock import create_autospec

from ...emitters import Emitter, LogLevel
from .common import ContextTestCase


class TestSubcontext(ContextTestCase):
    def test_no_emitter(self) -> None:
        cmp_subcontext = self.context.subcontext("message")

        self.assertEqual(self.context, cmp_subcontext.context)

    def test_default_log_level(self) -> None:
        emitter = create_autospec(Emitter)
        self.context.emitters = [emitter]

        cmp_subcontext = self.context.subcontext("message")

        emitter.log_message.assert_called_once_with(LogLevel.INFO, "message")

        self.assertEqual(self.context, cmp_subcontext.context)

    def test_log_level(self) -> None:
        emitter = create_autospec(Emitter)
        self.context.emitters = [emitter]

        cmp_subcontext = self.context.subcontext("message", log_level=LogLevel.ERROR)

        emitter.log_message.assert_called_once_with(LogLevel.ERROR, "message")

        self.assertEqual(self.context, cmp_subcontext.context)
