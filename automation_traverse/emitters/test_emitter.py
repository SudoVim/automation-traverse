import os
import unittest
from unittest.mock import MagicMock, create_autospec, patch

from .emitter import Emitter


class EmitterTestCase(unittest.TestCase):
    emitter: Emitter

    def setUp(self) -> None:
        self.emitter = Emitter()


class TestSubcontext(EmitterTestCase):
    def test(self) -> None:
        self.assertEqual(0, self.emitter.context_level)
        self.emitter.subcontext()
        self.assertEqual(1, self.emitter.context_level)


class TestPopSubcontext(EmitterTestCase):
    def test(self) -> None:
        self.emitter.context_level = 5
        self.emitter.pop_subcontext(3)
        self.assertEqual(3, self.emitter.context_level)


class TestLogFile(EmitterTestCase):
    @patch("builtins.open")
    def test(self, mock_open: MagicMock) -> None:
        cmp_fobj = self.emitter.log_file("descr", ".txt")

        mock_open.assert_called_once_with(os.devnull, "w")
        self.assertEqual(mock_open.return_value, cmp_fobj)
