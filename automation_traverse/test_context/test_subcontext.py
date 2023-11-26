import unittest
from ..context import TraverseSubcontext, TraverseContext
from ..emitters import Emitter
from unittest.mock import MagicMock, create_autospec


class SubcontextTestCase(unittest.TestCase):
    emitter: MagicMock
    context: MagicMock
    subcontext: TraverseSubcontext

    def setUp(self) -> None:
        self.emitter = create_autospec(Emitter)
        self.context = create_autospec(TraverseContext)
        self.context.log_position = 0
        self.context.emitters = [self.emitter]
        self.subcontext = TraverseSubcontext(self.context)


class TestEnter(SubcontextTestCase):
    def test(self) -> None:
        self.subcontext.__enter__()

        self.emitter.subcontext.assert_called_once_with()

    def test_no_emitters(self) -> None:
        self.context.emitters = []

        self.subcontext.__enter__()


class TestExit(SubcontextTestCase):
    def test(self) -> None:
        self.subcontext.__enter__()
        self.subcontext.__exit__()

        self.context.pop_subcontext.assert_called_once_with(0)
