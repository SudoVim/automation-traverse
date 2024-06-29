from typing import Any
from .common import ContextTestCase
from ...emitters import Emitter


class TestAddEmitter(ContextTestCase):
    def test(self) -> None:
        emitter = Emitter[Any]()
        self.assertEqual([], self.context.emitters)
        self.context.add_emitter(emitter)
        self.assertEqual([emitter], self.context.emitters)
