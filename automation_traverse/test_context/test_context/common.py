import unittest
from ...context import TraverseContext


class ContextTestCase(unittest.TestCase):
    context: TraverseContext

    def setUp(self) -> None:
        self.context = TraverseContext()
