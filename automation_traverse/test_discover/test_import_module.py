import typing
from unittest import TestCase
from unittest.mock import MagicMock, patch

from ..discover import import_module, imported_modules


class ImportModuleTests(TestCase):
    def setUp(self) -> None:
        super().setUp()

        imported_modules.clear()

    def test_found(self) -> None:
        imported_modules[("pypath", "filepath")] = typing

        cmp_module = import_module("pypath", "filepath")
        self.assertEqual(typing, cmp_module)

    @patch("automation_traverse.discover.importlib.util")
    def test_no_spec(self, mock_util: MagicMock) -> None:
        mock_util.spec_from_file_location.return_value = None

        with self.assertRaises(
            ValueError, msg="module ('pypath', 'filepath') not found"
        ):
            import_module("pypath", "filepath")

        mock_util.spec_from_file_location.assert_called_once_with("pypath", "filepath")

    @patch("automation_traverse.discover.importlib.util")
    def test_no_spec_loader(self, mock_util: MagicMock) -> None:
        spec = MagicMock()
        spec.loader = None
        mock_util.spec_from_file_location.return_value = spec

        with self.assertRaises(
            ValueError, msg="module ('pypath', 'filepath') not found"
        ):
            import_module("pypath", "filepath")

        mock_util.spec_from_file_location.assert_called_once_with("pypath", "filepath")

    @patch("automation_traverse.discover.importlib.util")
    def test_finds_module(self, mock_util: MagicMock) -> None:
        cmp_module = import_module("pypath", "filepath")

        new_module = mock_util.module_from_spec.return_value
        self.assertEqual(new_module, cmp_module)

        mock_util.spec_from_file_location.assert_called_once_with("pypath", "filepath")

        mock_spec = mock_util.spec_from_file_location.return_value
        mock_util.module_from_spec.assert_called_once_with(mock_spec)
        mock_spec.loader.exec_module.assert_called_once_with(new_module)

        self.assertEqual(
            {
                ("pypath", "filepath"): new_module,
            },
            imported_modules,
        )
