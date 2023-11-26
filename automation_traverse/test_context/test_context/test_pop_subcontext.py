from .common import ContextTestCase
from ...emitters import Emitter, LogLevel
from unittest.mock import create_autospec


class TestPopSubcontext(ContextTestCase):
    def test_no_emitter(self) -> None:
        self.context.pop_subcontext(5)

    def test_emitter(self) -> None:
        emitter = create_autospec(Emitter)
        self.context.emitters = [emitter]

        self.context.pop_subcontext(5)

        emitter.pop_subcontext.assert_called_once_with(5)
