from typing import Tuple
from unittest import TestCase
from unittest.mock import MagicMock

from ..context import TraverseFile


class TraverseFileTestCase(TestCase):
    def create_no_fobjs(self) -> TraverseFile:
        return TraverseFile([])

    def create_with_fobj(self) -> Tuple[TraverseFile, MagicMock]:
        fobj = MagicMock()
        cmp_file = TraverseFile([fobj])
        return cmp_file, fobj


class InitTest(TraverseFileTestCase):
    def test_init_no_fobjs(self) -> None:
        cmp_file = TraverseFile([])
        self.assertEqual([], cmp_file.fobjs)

    def test_init_with_fobj(self) -> None:
        fobj = MagicMock()
        cmp_file = TraverseFile([fobj])
        self.assertEqual([fobj], cmp_file.fobjs)


class EnterTest(TraverseFileTestCase):
    def test_enter(self) -> None:
        cmp_file = TraverseFile([])
        self.assertEqual(cmp_file, cmp_file.__enter__())


class ExitTest(TraverseFileTestCase):
    def test_exit(self) -> None:
        fobj = MagicMock()
        cmp_file = TraverseFile([fobj])
        cmp_file.__exit__()

        fobj.close.assert_called_once_with()


class WriteTest(TraverseFileTestCase):
    def test_write_no_fobjs(self) -> None:
        cmp_file = self.create_no_fobjs()
        cmp_file.write("some string")

    def test_write_fobj(self) -> None:
        cmp_file, fobj = self.create_with_fobj()
        cmp_file.write("some string")
        fobj.write.assert_called_once_with("some string")


class CloseTest(TraverseFileTestCase):
    def test_close_no_fobjs(self) -> None:
        cmp_file = self.create_no_fobjs()
        cmp_file.close()

    def test_close_fobj(self) -> None:
        cmp_file, fobj = self.create_with_fobj()
        cmp_file.close()
        fobj.close.assert_called_once_with()
