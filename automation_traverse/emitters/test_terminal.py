import sys
import unittest
from unittest.mock import MagicMock

from .terminal import TerminalEmitter


class TestInit(unittest.TestCase):
    def test_default_values(self) -> None:
        emitter = TerminalEmitter()

        self.assertTrue(emitter.use_color)
        self.assertEqual(4, emitter.context_level_spaces)
        self.assertTrue(emitter.flush)
        self.assertEqual(sys.stdout, emitter.fobj)

    def test_optional(self) -> None:
        fobj = MagicMock()
        emitter = TerminalEmitter(
            use_color=False,
            flush=False,
            fobj=fobj,
            context_level_spaces=3,
        )

        self.assertFalse(emitter.use_color)
        self.assertEqual(3, emitter.context_level_spaces)
        self.assertFalse(emitter.flush)
        self.assertEqual(fobj, emitter.fobj)


class TerminalEmitterTestCase(unittest.TestCase):
    fobj: MagicMock
    emitter: TerminalEmitter

    def setUp(self) -> None:
        self.fobj = MagicMock()
        self.emitter = TerminalEmitter(fobj=self.fobj)


class TestEmit(TerminalEmitterTestCase):
    def test_no_flush(self) -> None:
        self.emitter.flush = False

        self.emitter.emit("message")

        self.fobj.write.assert_called_once_with("message")
        self.fobj.flush.assert_not_called()

    def test_flush(self) -> None:
        self.emitter.emit("message")

        self.fobj.write.assert_called_once_with("message")
        self.fobj.flush.assert_called_once_with()
